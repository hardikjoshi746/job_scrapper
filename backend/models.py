import uuid
from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from database import Base


def _uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255))
    created_at = Column(DateTime, default=func.now())


class Application(Base):
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    job_title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255))
    job_url = Column(Text)
    status = Column(String(50), default="saved")  # saved / applied / interview / offer / rejected
    applied_date = Column(Date)
    follow_up_date = Column(Date)
    notes = Column(Text)
    hiring_manager_name = Column(String(255))
    hiring_manager_email = Column(String(255))
    job_description = Column(Text)
    tailored_resume_path = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class BaseResume(Base):
    __tablename__ = "base_resumes"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    filename = Column(String(255))
    file_path = Column(Text)
    extracted_text = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class ScrapedJob(Base):
    __tablename__ = "scraped_jobs"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    source = Column(String(50), nullable=False)        # google_jobs | linkedin | adzuna | remoteok | arbeitnow | weworkremotely | indeed_rss
    job_url = Column(Text, nullable=False, index=True)
    title = Column(String(512), nullable=False)
    company = Column(String(255))
    location = Column(String(255))
    description = Column(Text)
    salary_min = Column(Integer)
    salary_max = Column(Integer)
    currency = Column(String(10))
    tags = Column(Text)                                # JSON-encoded list
    posted_at = Column(DateTime)
    fetched_at = Column(DateTime, default=func.now())
    is_remote = Column(Boolean, default=False)
