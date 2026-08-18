from pydantic import BaseModel, Field
from typing import Optional, List, Literal

# Valid Job Application Statuses
ApplicationStatus = Literal[
    "APPLIED",
    "UNDER_REVIEW",
    "ASSESSMENT_INVITED",
    "INTERVIEW_INVITED",
    "OFFER_RECEIVED",
    "REJECTED",
    "ACTION_REQUIRED",
    "ARCHIVED"
]

# Schema used for LLM Extraction Output
class ExtractedJobDetails(BaseModel):
    is_job_related: bool
    company_name: str
    job_title: str
    job_reference_id: Optional[str] = None
    status: Literal[
        "APPLIED",
        "UNDER_REVIEW",
        "ASSESSMENT_INVITED",
        "INTERVIEW_INVITED",
        "OFFER_RECEIVED",
        "REJECTED",
        "ACTION_REQUIRED",
        "NOT_JOB_RELATED"
    ]
    summary: str
    action_required: Optional[str] = None
    next_step_deadline: Optional[str] = None

# Request Payload to Process an Incoming Raw Email
class RawEmailInput(BaseModel):
    sender: str
    subject: str
    body: str
    email_message_id: Optional[str] = None
    email_thread_id: Optional[str] = None
    email_deep_link: Optional[str] = None
    received_at: Optional[str] = None

# Response when an email is processed
class ProcessEmailResponse(BaseModel):
    success: bool
    is_job_related: bool
    matched_existing_application: bool
    application_id: Optional[int] = None
    company_name: Optional[str] = None
    status: Optional[str] = None
    message: str
    extraction: Optional[ExtractedJobDetails] = None

# Timeline Event Model
class TimelineEventResponse(BaseModel):
    id: int
    application_id: int
    email_message_id: Optional[str]
    email_thread_id: Optional[str]
    sender: str
    subject: str
    received_at: str
    summary: str
    extracted_status: str
    email_deep_link: Optional[str]
    created_at: str

# Application Card Model
class ApplicationResponse(BaseModel):
    id: int
    company_name: str
    company_slug: str
    job_title: str
    job_reference_id: Optional[str]
    status: str
    action_required: Optional[str]
    next_step_deadline: Optional[str]
    interview_date: Optional[str]
    location: Optional[str]
    salary: Optional[str]
    notes: Optional[str]
    email_count: Optional[int] = 0
    last_email_date: Optional[str] = None
    created_at: str
    updated_at: str
    timeline: Optional[List[TimelineEventResponse]] = None

# Manual Application Creation Request
class CreateApplicationRequest(BaseModel):
    company_name: str
    job_title: str
    job_reference_id: Optional[str] = None
    status: Optional[str] = "APPLIED"
    action_required: Optional[str] = None
    next_step_deadline: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None

# Application Update Request
class UpdateApplicationRequest(BaseModel):
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    job_reference_id: Optional[str] = None
    status: Optional[str] = None
    action_required: Optional[str] = None
    next_step_deadline: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
