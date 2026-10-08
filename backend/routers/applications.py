from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from typing import List
from services.imagekit_service import upload_resume_to_imagekit
from pydantic import BaseModel
from models import Application, ApplicationStatus, ApplicationUpdate, Job, UserRole, User, Interview
from dependencies import require_role, get_current_user
from beanie import PydanticObjectId
from datetime import datetime, timedelta
from services.backgroundtasks import compute_resume_embedding_task, send_email, generate_and_save_questions_task
from services.views import applications_with_details, jobs_by_id, users_by_id
import jwt
from config import settings

SECRET_KEY=settings.JWT_SECRET
router = APIRouter(prefix="/applications", tags=["applications"])


class ApplyRequest(BaseModel):
    job_id: str
    resume_url: str


@router.post("/", response_model=Application)
async def apply_to_job(
    background_tasks: BackgroundTasks,
    job_id: str = Form(...),
    resume: UploadFile = File(...),
    candidate=Depends(require_role(UserRole.candidate))
):
    # 1. Validate file type
    allowed_extensions = {".pdf", ".docx", ".txt"}
    file_ext = resume.filename.rsplit(
        '.', 1)[-1].lower() if resume.filename else ""

    if f".{file_ext}" not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # 2. Check job existence
    job = await Job.get(PydanticObjectId(job_id))
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # 3. Check if already applied
    existing = await Application.find_one(
        Application.job_id == job_id,
        Application.candidate_id == str(candidate.id)
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already applied to this job"
        )

    # 4. Read resume bytes once
    resume_bytes = await resume.read()
    await resume.seek(0)  # reset for upload

    # 5. Upload to ImageKit
    resume_url = await upload_resume_to_imagekit(resume)

    # 6. Create new Application
    application = Application(
        job_id=job_id,
        candidate_id=str(candidate.id),
        resume_url=resume_url,
        status=ApplicationStatus.applied,
        applied_at=datetime.utcnow(),
    )
    await application.insert()

    # 7. Add application ID to Job
    job.application_ids.append(str(application.id))
    await job.save()

    # 8. Schedule background embedding generation
    background_tasks.add_task(
        compute_resume_embedding_task,
        application_id=str(application.id),
        file_bytes=resume_bytes,
        filename=resume.filename,
        content_type=resume.content_type
    )

    return application


@router.get("/", response_model=List[dict])
async def get_applications(candidate=Depends(require_role(UserRole.candidate))):
    """
    The candidate's applications, with job info and their interview (if any).

    FIX: the candidate had no way to open their interview except the email
    link, and the Results tab was always empty. Each row now carries its
    interview id, status and (once finished) score.
    FIX: one query per related collection instead of two queries per row.
    """
    applications = await Application.find(
        Application.candidate_id == str(candidate.id)
    ).to_list()

    jobs = await jobs_by_id(a.job_id for a in applications)
    recruiters = await users_by_id(j.recruiter_id for j in jobs.values())
    app_ids = [str(a.id) for a in applications]
    interviews = await Interview.find({"application_id": {"$in": app_ids}}).to_list() if app_ids else []
    interview_for = {i.application_id: i for i in interviews}

    results = []
    for app in sorted(applications, key=lambda a: a.applied_at, reverse=True):
        job = jobs.get(app.job_id)
        recruiter = recruiters.get(job.recruiter_id) if job else None
        iv = interview_for.get(str(app.id))
        result = (iv.result or {}) if iv else {}

        results.append({
            "id": str(app.id),
            "title": job.title if job else "Unknown",
            "company": recruiter.name if recruiter else "Unknown",
            "appliedAt": app.applied_at.strftime("%d %b %Y"),
            "status": app.status.value.capitalize(),
            "interview": {
                "id": str(iv.id),
                "status": iv.status.value,
                "score": result.get("overall_score"),
                "performance": result.get("performance"),
            } if iv else None,
        })

    return results


@router.get("/recruiter", response_model=List[dict])
async def get_all_applications_for_recruiter(recruiter=Depends(require_role(UserRole.recruiter))):
    """
    Every application to every job this recruiter posted, best match first.

    FIX: the Candidates tab only worked after clicking "View candidates" on a
    job. Opening the tab directly sent no request at all and showed nothing.
    """
    jobs = await Job.find(Job.recruiter_id == str(recruiter.id)).to_list()
    job_ids = [str(j.id) for j in jobs]
    applications = await Application.find({"job_id": {"$in": job_ids}}).to_list() if job_ids else []
    return await applications_with_details(applications)


@router.get("/job/{job_id}", response_model=List[Application])
async def get_applications_for_job(job_id: str, recruiter=Depends(require_role(UserRole.recruiter))):
    job = await Job.get(PydanticObjectId(job_id))
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.recruiter_id != str(recruiter.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to view applications for this job")
    applications = await Application.find(Application.job_id == job_id).to_list()
    return applications


@router.patch("/{application_id}", response_model=Application)
async def update_application_status(
    application_id: str,
    update: ApplicationUpdate,
    background_tasks: BackgroundTasks,  # ⬅️ add this
    recruiter=Depends(require_role(UserRole.recruiter)),
):
    # 1️⃣ Fetch application
    application = await Application.get(PydanticObjectId(application_id))
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
        )

    # 2️⃣ Verify job & recruiter ownership
    job = await Job.get(PydanticObjectId(application.job_id))
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    if job.recruiter_id != str(recruiter.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this application",
        )

    # 3️⃣ Apply status update
    if update.status is not None:
        application.status = update.status
        await application.save()

        # 4️⃣ If moved to interview, create Interview + enqueue email
        if update.status == ApplicationStatus.interview:
            candidate = await User.get(PydanticObjectId(application.candidate_id))

            existing_interview = await Interview.find_one(
                Interview.application_id == application_id
            )

            if existing_interview:
                interview = existing_interview
            else:
                interview = Interview(
                    application_id=application_id,
                    recruiter_id=str(recruiter.id),
                    scheduled_at=datetime.utcnow(),
                )
                await interview.insert()

            interview_url = f"{settings.FRONTEND_URL}/interview/{interview.id}"

            interview.meeting_url = interview_url
            await interview.save()

            # Compose email
            subject = f"Interview Scheduled for {job.title}"
            body = f"""
            Hi {candidate.name},

            Congratulations! You've been shortlisted for an interview for the position of "{job.title}".

            Interview Link: {interview_url}

            Please join at your scheduled time.
            
            Best,
            {recruiter.name}
            """

            # ⬅️ Offload email sending and question generation to background task
            background_tasks.add_task(generate_and_save_questions_task, interview.id, job.description, application.resume_text)
            background_tasks.add_task(
                send_email, candidate.email, subject, body)

    return application
