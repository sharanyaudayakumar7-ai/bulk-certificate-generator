from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from .models import JobStatus, CertificateStatus

class RecipientInput(BaseModel):
    name: str = Field(..., min_length=1, description="Recipient's full name")
    email: EmailStr = Field(..., description="Recipient's email address")

class JobCreateRequest(BaseModel):
    event_name: str = Field(..., min_length=1, description="Name of the event")
    date: str = Field(..., min_length=1, description="Date of the event")
    recipients: List[RecipientInput] = Field(..., min_length=1, description="List of recipients")

class CertificateResponse(BaseModel):
    id: int
    job_id: int
    recipient_name: str
    recipient_email: str
    status: CertificateStatus
    file_path: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True

class JobResponse(BaseModel):
    id: int
    status: JobStatus
    total_recipients: int
    successful_generations: int
    failed_generations: int
    created_at: datetime

    class Config:
        from_attributes = True
