from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import date, datetime
from typing import Optional


# --- Auth Schemas ---

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    email: str
    name: Optional[str]

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    name: Optional[str]
    created_at: datetime


# --- Application Schemas ---

class ApplicationCreate(BaseModel):
    job_title: str
    company: str
    location: Optional[str] = None
    job_url: Optional[str] = None
    status: Optional[str] = "saved"
    applied_date: Optional[date] = None
    follow_up_date: Optional[date] = None
    notes: Optional[str] = None
    hiring_manager_name: Optional[str] = None
    hiring_manager_email: Optional[str] = None
    job_description: Optional[str] = None


class ApplicationUpdate(BaseModel):
    job_title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    job_url: Optional[str] = None
    status: Optional[str] = None
    applied_date: Optional[date] = None
    follow_up_date: Optional[date] = None
    notes: Optional[str] = None
    hiring_manager_name: Optional[str] = None
    hiring_manager_email: Optional[str] = None
    job_description: Optional[str] = None


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_title: str
    company: str
    location: Optional[str]
    job_url: Optional[str]
    status: str
    applied_date: Optional[date]
    follow_up_date: Optional[date]
    notes: Optional[str]
    hiring_manager_name: Optional[str]
    hiring_manager_email: Optional[str]
    job_description: Optional[str]
    tailored_resume_path: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]


# --- Resume Schemas ---

class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    file_path: str
    is_active: bool
    created_at: datetime