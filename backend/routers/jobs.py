from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List
from models import (Job, JobUpdate, JobResponse, User, UserRole, Application,
                    ApplicationStatus, Interview, InterviewStatus)
from dependencies import require_role, get_current_user
from beanie import PydanticObjectId
from datetime import datetime, timedelta
from utils import humanize_posted_at
from bson import ObjectId
from services.backgroundtasks import compute_job_description_embedding_task
from services.views import applications_with_details, users_by_id

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/", response_model=Job)
async def create_job(
    background_tasks: BackgroundTasks,
    job: JobUpdate,
    recruiter=Depends(require_role(UserRole.recruiter))
):
    """Create a new job posting and generate embedding for the job description."""
    new_job = Job(
        title=job.title,
        description=job.description,
        location=job.location,
        type=job.type,
        tags=job.tags,
        recruiter_id=str(recruiter.id),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    await new_job.insert()

    # Generate job description embedding in background
    background_tasks.add_task(
        compute_job_description_embedding_task,
        job_id=str(new_job.id),
        job_description=job.description
    )

    return new_job


@router.get("/", response_model=List[JobResponse])
async def list_jobs(candidate=Depends(require_role(UserRole.candidate))):
    """
    Return all jobs that the candidate has NOT applied to.
    """
    applied_applications = await Application.find(
        Application.candidate_id == str(candidate.id)
    ).to_list()
    applied_job_ids = [ObjectId(app.job_id) for app in applied_applications]

    jobs = await Job.find(
        {"_id": {"$nin": applied_job_ids}}
    ).to_list()

    # One query for all recruiter names instead of one per job (N+1 fix)
    recruiters = await users_by_id(j.recruiter_id for j in jobs)

    result = []
    for job in jobs:
        recruiter = recruiters.get(job.recruiter_id)
        recruiter_name = recruiter.name if recruiter else None

        result.append(JobResponse(
            id=str(job.id),
            title=job.title,
            description=job.description,
            recruiter_name=recruiter_name,
            location=job.location,
            type=job.type,
            tags=job.tags,
            postedAt=humanize_posted_at(job.created_at),
        ))

    return result


@router.get("/my")
async def get_recruiter_jobs(recruiter=Depends(require_role(UserRole.recruiter))):
    """
    Fetch all jobs posted by the logged-in recruiter.
    Returns data shaped for Recruiter Dashboard.
    """
    jobs = await Job.find(Job.recruiter_id == str(recruiter.id)).to_list()

    response = []
    for job in jobs:
        response.append({
            "id": str(job.id),
            "title": job.title,
            "description": job.description,  # needed by the Edit dialog
            "tags": job.tags,
            "location": job.location,
            "type": job.type,
            "applicants": len(job.application_ids),
            "status": "Open",
            "updatedAt": job.updated_at.strftime("%d %b %Y"),
        })

    return response


@router.get("/stats")
async def get_recruiter_stats(recruiter=Depends(require_role(UserRole.recruiter))):
    """
    Real numbers for the Overview tab.
    FIX: the stats cards and pipeline chart were hard-coded sample data
    ("12 active jobs", "48 new candidates") no matter what was in the database.
    """
    rid = str(recruiter.id)
    jobs = await Job.find(Job.recruiter_id == rid).to_list()
    job_ids = [str(j.id) for j in jobs]
    apps = await Application.find({"job_id": {"$in": job_ids}}).to_list() if job_ids else []
    interviews = await Interview.find(Interview.recruiter_id == rid).to_list()

    week_ago = datetime.utcnow() - timedelta(days=7)
    pipeline = {s.value: 0 for s in ApplicationStatus}
    for a in apps:
        pipeline[a.status.value] = pipeline.get(a.status.value, 0) + 1

    upcoming = {InterviewStatus.scheduled, InterviewStatus.in_progress}
    return {
        "active_jobs": len(jobs),
        "total_candidates": len(apps),
        "new_candidates_7d": sum(1 for a in apps if a.applied_at and a.applied_at >= week_ago),
        "interviews_scheduled": sum(1 for i in interviews if i.status in upcoming),
        "interviews_completed": sum(1 for i in interviews if i.status == InterviewStatus.completed),
        "offer_rate": round(pipeline["offer"] / len(apps) * 100) if apps else 0,
        "pipeline": [
            {"stage": "Applied", "count": pipeline["applied"]},
            {"stage": "Screening", "count": pipeline["reviewed"]},
            {"stage": "Interview", "count": pipeline["interview"]},
            {"stage": "Offer", "count": pipeline["offer"]},
            {"stage": "Rejected", "count": pipeline["rejected"]},
        ],
    }


@router.get("/{job_id}/ranked")
async def get_ranked_applications_by_job(
    job_id: str,
    recruiter=Depends(require_role(UserRole.recruiter))
):
    """
    All applications for one job, best match first.

    FIX: applications whose match score was still being calculated (or failed)
    were filtered out, so new applicants were invisible. They now appear last.
    FIX: the response included each candidate's password hash and 384-number
    embeddings; it now sends only what the table needs.
    """
    job = await Job.get(PydanticObjectId(job_id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.recruiter_id != str(recruiter.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to view this job's applications")

    applications = await Application.find(Application.job_id == job_id).to_list()
    return await applications_with_details(applications)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    job = await Job.get(PydanticObjectId(job_id))
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    recruiter_name = None
    if job.recruiter_id:
        recruiter = await User.get(job.recruiter_id)
        if recruiter:
            recruiter_name = recruiter.name

    return JobResponse(
        id=str(job.id),
        title=job.title,
        description=job.description,
        recruiter_name=recruiter_name,
        location=job.location,
        type=job.type,
        tags=job.tags,
        postedAt=humanize_posted_at(job.created_at),
    )

# ---------------- UPDATE JOB ----------------


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    job_update: JobUpdate,
    background_tasks: BackgroundTasks,
    recruiter=Depends(require_role(UserRole.recruiter)),
):
    job = await Job.get(PydanticObjectId(job_id))
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.recruiter_id != str(recruiter.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to update this job")

    # Update only provided fields
    for field, value in job_update.dict(exclude_unset=True).items():
        setattr(job, field, value)

    job.updated_at = datetime.utcnow()

    # A new description needs a new embedding, or match scores go stale.
    if job_update.description is not None:
        background_tasks.add_task(
            compute_job_description_embedding_task, job_id=str(job.id),
            job_description=job.description)
    await job.save()

    recruiter_name = recruiter.name

    return JobResponse(
        id=str(job.id),
        title=job.title,
        description=job.description,
        recruiter_name=recruiter_name,
        location=job.location,
        type=job.type,
        tags=job.tags,
        postedAt=humanize_posted_at(job.created_at),
    )

# ---------------- DELETE JOB ----------------


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id: str, recruiter=Depends(require_role(UserRole.recruiter))):
    job = await Job.get(PydanticObjectId(job_id))
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.recruiter_id != str(recruiter.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Not authorized to delete this job")

    await job.delete()
    return None
