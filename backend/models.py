from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Boolean
from sqlalchemy.sql import func
from database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
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

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255))
    file_path = Column(Text)
    extracted_text = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())