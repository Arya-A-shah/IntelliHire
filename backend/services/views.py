"""
Helpers that turn database documents into the JSON the dashboards show.

They load related users/jobs in ONE query each (`$in`), instead of one query
per row (the "N+1 queries" problem the old routes had), and they never send
password hashes, resume text or 384-number embeddings to the browser.
"""
from typing import Any, Dict, Iterable, List, Optional

from beanie import PydanticObjectId

from models import Application, Interview, Job, User


def _oid(value) -> Optional[PydanticObjectId]:
    try:
        return PydanticObjectId(value)
    except Exception:
        return None


async def users_by_id(ids: Iterable[str]) -> Dict[str, User]:
    oids = [o for o in {_oid(i) for i in ids} if o]
    users = await User.find({"_id": {"$in": oids}}).to_list() if oids else []
    return {str(u.id): u for u in users}


async def jobs_by_id(ids: Iterable[str]) -> Dict[str, Job]:
    oids = [o for o in {_oid(i) for i in ids} if o]
    jobs = await Job.find({"_id": {"$in": oids}}).to_list() if oids else []
    return {str(j.id): j for j in jobs}


async def applications_by_id(ids: Iterable[str]) -> Dict[str, Application]:
    oids = [o for o in {_oid(i) for i in ids} if o]
    apps = await Application.find({"_id": {"$in": oids}}).to_list() if oids else []
    return {str(a.id): a for a in apps}


def sort_by_match(apps: List[Application]) -> List[Application]:
    """Highest match first; applications still being scored go last."""
    return sorted(apps, key=lambda a: (a.match_score is None, -(a.match_score or 0)))


def application_details(app: Application, users: Dict[str, User], jobs: Dict[str, Job]) -> Dict[str, Any]:
    data = app.model_dump(
        mode="json", by_alias=True,
        exclude={"resume_embedding", "resume_text", "embedding_error"},
    )
    data["_id"] = str(app.id)
    cand = users.get(app.candidate_id)
    job = jobs.get(app.job_id)
    data["candidate"] = {"_id": str(cand.id), "name": cand.name, "email": cand.email} if cand else None
    data["job"] = (
        {"_id": str(job.id), "title": job.title, "location": job.location, "type": job.type}
        if job else None
    )
    return data


async def applications_with_details(apps: List[Application]) -> List[Dict[str, Any]]:
    users = await users_by_id(a.candidate_id for a in apps)
    jobs = await jobs_by_id(a.job_id for a in apps)
    return [application_details(a, users, jobs) for a in sort_by_match(apps)]


def report_status_of(interview: Interview) -> str:
    """'ready', 'failed' or 'pending' for an interview's written report."""
    result = interview.result or {}
    if interview.report:
        return "ready"
    if result.get("error") or result.get("report_error"):
        return "failed"
    return "pending"
