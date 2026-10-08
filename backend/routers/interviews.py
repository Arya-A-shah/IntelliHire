import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from models import Interview, InterviewCreate, Application, Job, UserRole, TokenResponse, InterviewStatus
from dependencies import require_role
from livekit import rtc, api
from beanie import PydanticObjectId
from beanie.exceptions import DocumentNotFound
from datetime import datetime
from pydantic import ValidationError
from config import settings
from datetime import timedelta
from sharedstate import active_sessions
from services.livekit_service import start_video_processor, stop_video_processor
from services.backgroundtasks import generate_and_save_questions_task, questions_in_progress
from services.views import (applications_by_id, application_details, jobs_by_id,
                            report_status_of, users_by_id)
from core.socket import sio

LIVEKIT_URL = settings.LIVEKIT_URL
LIVEKIT_API_KEY = settings.LIVEKIT_API_KEY
LIVEKIT_API_SECRET = settings.LIVEKIT_API_SECRET
PROC_NS = "/proc"
_background = set()

router = APIRouter(prefix="/interviews", tags=["interviews"])


@router.post("/", response_model=Interview)
async def create_interview(interview_data: InterviewCreate, recruiter=Depends(require_role(UserRole.recruiter))):
    application = await Application.get(PydanticObjectId(interview_data.application_id))
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    job = await Job.get(PydanticObjectId(application.job_id))
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.recruiter_id != str(recruiter.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to create interview for this application")
    interview = Interview(
        application_id=interview_data.application_id,
        recruiter_id=str(recruiter.id),
        scheduled_at=interview_data.scheduled_at,
        notes=interview_data.notes,
    )
    await interview.insert()
    return interview


@router.get("/my")
async def get_my_interviews(recruiter=Depends(require_role(UserRole.recruiter))):
    """
    All interviews for this recruiter's candidates, newest first.

    FIX: the Interviews tab was a hard-coded "No interviews scheduled" message.
    """
    interviews = await Interview.find(Interview.recruiter_id == str(recruiter.id)).to_list()
    apps = await applications_by_id(i.application_id for i in interviews)
    users = await users_by_id(a.candidate_id for a in apps.values())
    jobs = await jobs_by_id(a.job_id for a in apps.values())

    rows = []
    for iv in interviews:
        app = apps.get(iv.application_id)
        result = iv.result or {}
        rows.append({
            "interview_id": str(iv.id),
            "status": iv.status.value,
            "scheduled_at": iv.scheduled_at.isoformat() if iv.scheduled_at else None,
            "meeting_url": iv.meeting_url,
            "questions_ready": bool(iv.questions),
            "score": result.get("overall_score"),
            "performance": result.get("performance"),
            "integrity_grade": (iv.integrity_score or {}).get("grade"),
            "report_status": report_status_of(iv),
            "application": application_details(app, users, jobs) if app else None,
        })

    rows.sort(key=lambda r: r["scheduled_at"] or "", reverse=True)
    return rows


@router.get("/job/{job_id}", response_model=List[Interview])
async def get_interviews_for_job(job_id: str, recruiter=Depends(require_role(UserRole.recruiter))):
    job = await Job.get(PydanticObjectId(job_id))
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.recruiter_id != str(recruiter.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to view interviews for this job")
    # Find applications for this job
    applications = await Application.find(Application.job_id == job_id).to_list()
    application_ids = [str(app.id) for app in applications]
    interviews = await Interview.find({"application_id": {"$in": application_ids}}).to_list()
    return interviews


# Conducting interview

@router.post("/start/{interview_id}", response_model=TokenResponse)
async def start_interview(interview_id: PydanticObjectId, candidate = Depends(require_role(UserRole.candidate))):
    """
    Start a new interview session and generate LiveKit access token
    """
    try:
        # if str(interview_id) in active_sessions:
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="Interview already started."
        #     )
            
        # check if the candidate has an interview scheduled
        interview: Optional[Interview] = await Interview.get(interview_id)
        if not interview:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview not found."
            )

        
        # Fetch associated application
        app_id = PydanticObjectId(interview.application_id)
        application: Optional[Application] = await Application.get(app_id)
        if not application:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Associated application not found."
            )

        # FIX: any logged-in candidate with the link could start someone
        # else's interview. Only the candidate who applied may start it.
        if application.candidate_id != str(candidate.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This interview belongs to another candidate."
            )

        # A finished interview must not be restarted: that would reset its
        # status and overwrite the transcript the report was built from.
        if interview.status == InterviewStatus.completed:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This interview has already been completed."
            )

        # FIX: fail early with a clear message instead of letting the AI
        # socket be refused later with no explanation.
        if not interview.questions:
            # FIX: if generation failed earlier (e.g. Gemini 503), nothing ever
            # retried it. Opening the link now restarts it in the background.
            if str(interview_id) not in questions_in_progress:
                job = await Job.get(PydanticObjectId(application.job_id))
                # Not BackgroundTasks: FastAPI skips those when the route
                # raises an HTTPException, which we do right below.
                task = asyncio.create_task(generate_and_save_questions_task(
                    interview.id, job.description if job else "", application.resume_text))
                _background.add(task)  # keep a reference so it isn't garbage-collected
                task.add_done_callback(_background.discard)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Your interview questions are still being prepared. Please try again in a minute."
            )

        # Ensure same-day start
        # scheduled_date = interview.scheduled_at.date() if interview.scheduled_at else None
        # today = datetime.utcnow().date()
        # # if not interview.scheduled_at or interview.status != InterviewStatus.scheduled or scheduled_date != today:
        # if not interview.scheduled_at or scheduled_date != today:
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="Interview not yet scheduled or not scheduled today."
        #     )

        # Livekit token & session logic
        room_name = f"interview_{str(interview_id)}"
        token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        token.with_identity(str(candidate.id))
        token.with_name(candidate.name)
        token.with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
        token.with_ttl(timedelta(hours=2))
        jwt_token = token.to_jwt()

        # Store session info
        # FIX: only create the session once. Calling /start again (page
        # refresh, React StrictMode) used to wipe the saved socket ids and
        # the proctoring results of the running interview.
        key = str(interview_id)
        if key not in active_sessions or active_sessions[key].get("status") != "active":
            active_sessions[key] = {
                "interview_id": key,
                "room_name": room_name,
                "candidate_id": str(candidate.id),
                "candidate_name": candidate.name,
                "status": "active",
                "ai_socket_id": None,
                "proc_socket_id": None,
                "score": 0
            }

        await start_video_processor(interview_id, room_name)

        # Update interview status to in_progress
        interview.status = InterviewStatus.in_progress
        await interview.save()
        
        return TokenResponse(
            token=jwt_token,
            room_name=room_name,
            url=LIVEKIT_URL
        )

    except DocumentNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview or related application not found."
        )

    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data format: {e.errors()}"
        )

    except HTTPException:
        raise  # Re-throw HTTP errors directly

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error starting interview: {str(e)}"
        )
    

@router.post("/end/{interview_id}")
async def end_interview(interview_id: PydanticObjectId, candidate = Depends(require_role(UserRole.candidate))):
    """
    End an interview session
    """
    # FIX: the dict keys are strings but interview_id is an ObjectId, so the
    # old `interview_id in active_sessions` check was always False -> 404.
    key = str(interview_id)
    if key in active_sessions:
        active_sessions[key]["status"] = "ended"
        # update interview status in database
        # Update interview status in DB
        interview = await Interview.get(interview_id)
        if interview:
            interview.status = InterviewStatus.completed
            # interview.transcript = active_sessions[interview_id].get("transcript", interview.transcript)
            await interview.save()
            
        # add transcript to database which is in interview.py in conversation_sessions variable
        # add report generation task in queue
        
        # Clean up memory
        del active_sessions[key]

        # Stop video processor
        await stop_video_processor(interview_id)

        # Disconnect users from LiveKit room
        await sio.close_room(room=f"interview_{str(interview_id)}", namespace=PROC_NS)

        return {"message": "Interview ended successfully"}

    
    raise HTTPException(status_code=404, detail="Interview not found")


@router.get("/report/{application_id}")
async def get_interview_report(
    application_id: PydanticObjectId,
    recruiter=Depends(require_role(UserRole.recruiter))
):
    # Fetch the interview by application_id
    interview = await Interview.find_one(Interview.application_id == str(application_id))

    if not interview:
        # Not an error: this candidate simply hasn't been shortlisted yet.
        return {"application_id": str(application_id), "report_status": "no_interview"}

    # Ensure recruiter has permission
    if interview.recruiter_id != str(recruiter.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this interview report."
        )

    # Check if report exists
    result = interview.result or {}

    # FIX: the old code used getattr(interview.result, "overall_score"), but
    # result is a dict, so score and details were always null. It also
    # returned 404 while the report was still being written, which the UI
    # showed as an error. Now we always answer and say which state it's in.
    report_status = report_status_of(interview)

    return {
        "application_id": interview.application_id,
        "interview_id": str(interview.id),
        "status": interview.status,
        "report_status": report_status,
        "report": interview.report,
        "error": result.get("error") or result.get("report_error"),
        "score": result.get("overall_score"),
        "performance": result.get("performance"),
        "details": result.get("details"),
        "integrity_score": interview.integrity_score,
        "integrity_report": interview.integrity_report,
    }
