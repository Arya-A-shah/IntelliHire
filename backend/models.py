from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class UserRole(str, Enum):
    candidate = "candidate"
    recruiter = "recruiter"
    admin = "admin"


class User(Document):
    name: str
    email: EmailStr = Indexed(unique=True)
    hashed_password: str
    role: UserRole
    resume_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"


class UserUpdate(BaseModel):
    name: Optional[str] = None
    resume_url: Optional[str] = None


class Job(Document):
    title: str
    description: str
    recruiter_id: str
    location: str
    type: str
    tags: List[str] = Field(default_factory=list)
    application_ids: List[str] = Field(default_factory=list)
    job_description_embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "jobs"


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    type: Optional[str] = None
    tags: Optional[List[str]] = None


class JobResponse(BaseModel):
    id: str
    title: str
    description: str
    recruiter_name: Optional[str]
    location: str
    type: str
    tags: List[str]
    postedAt: str


class ApplicationStatus(str, Enum):
    applied = "applied"
    reviewed = "reviewed"
    interview = "interview"
    rejected = "rejected"
    offer = "offer"
    

class Application(Document):
    job_id: str
    candidate_id: str
    resume_url: Optional[str] = None
    resume_text: Optional[str] = None
    status: ApplicationStatus = ApplicationStatus.applied
    applied_at: datetime = Field(default_factory=datetime.utcnow)
    resume_embedding: Optional[List[float]] = None
    embedding_error: Any = None
    match_score: Optional[float] = None

    class Settings:
        name = "applications"


class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus]


class InterviewStatus(str, Enum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    no_show = "no_show"
    rescheduled = "rescheduled"


class Interview(Document):
    application_id: str
    recruiter_id: str
    scheduled_at: Optional[datetime]
    status: InterviewStatus = InterviewStatus.scheduled
    notes: Optional[str] = None
    transcript: Optional[List[Dict[str, Any]]] = None
    meeting_url: Optional[str] = None
    questions: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    result: Optional[Dict[str, Any]] = Field(default_factory=dict)
    report: Optional[str] = None
    integrity_score: Optional[Dict[str, Any]] = None
    integrity_report: Optional[Dict[str, Any]] = None

    class Settings:
        name = "interviews"


class InterviewCreate(BaseModel):
    application_id: str
    scheduled_at: Optional[datetime]
    notes: Optional[str] = None


class TokenResponse(BaseModel):
    token: str
    room_name: str
    url: str


class ApplicationWithDetails(Application):
    candidate: Optional["User"] = None
    job: Optional["Job"] = None
