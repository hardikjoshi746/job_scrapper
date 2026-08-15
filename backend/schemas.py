from pydantic import BaseModel, ConfigDict, EmailStr
from datetime import date, datetime
from typing import Optional, List


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
    user_id: str
    email: str
    name: Optional[str]

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
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

    id: str
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

    id: str
    filename: str
    file_path: str
    is_active: bool
    created_at: datetime


# --- Scraper Schemas ---

class ScrapeRequest(BaseModel):
    keyword: str
    location: Optional[str] = "remote"
    sources: Optional[List[str]] = None        # None = all sources
    experience_level: Optional[str] = None    # entry | associate | mid | senior | lead
    date_posted: Optional[str] = None         # any | day | week | month

class ScrapedJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source: str
    job_url: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    currency: Optional[str] = None
    tags: Optional[List[str]] = None
    posted_at: Optional[datetime] = None
    is_remote: bool = False

class ScrapeResponse(BaseModel):
    total: int
    sources: dict
    results: List[ScrapedJobOut]
    errors: dict

class SaveScrapedJobRequest(BaseModel):
    job_url: str
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    job_description: Optional[str] = None