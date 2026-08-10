import os
import tempfile
import aiofiles
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from dependencies import get_db, get_current_user
from models import BaseResume, Application, User
from services.resume_parser import extract_text
from services.claude import tailor_resume
from services.pdf_generator import generate_pdf
from services.s3 import upload_file, get_presigned_url
from config import settings

router = APIRouter()

# Use S3 in prod (when bucket is configured), local disk in dev
USE_S3 = bool(settings.s3_bucket)
UPLOAD_DIR = "uploads"
GENERATED_DIR = "generated"

if not USE_S3:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(GENERATED_DIR, exist_ok=True)


@router.post("/upload")
async def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_bytes = await file.read()

    if USE_S3:
        # Write to temp file to extract text, then upload to S3
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name
        try:
            extracted = extract_text(tmp_path)
            s3_key = f"uploads/{current_user.id}/{file.filename}"
            upload_file(tmp_path, s3_key)
        finally:
            os.unlink(tmp_path)
        stored_path = s3_key
    else:
        local_path = os.path.join(UPLOAD_DIR, file.filename)
        async with aiofiles.open(local_path, "wb") as f:
            await f.write(file_bytes)
        extracted = extract_text(local_path)
        stored_path = local_path

    db.query(BaseResume).filter(BaseResume.user_id == current_user.id).update({"is_active": False})
    db_resume = BaseResume(
        user_id=current_user.id,
        filename=file.filename,
        file_path=stored_path,
        extracted_text=extracted,
        is_active=True,
    )
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    return {"resume_id": db_resume.id, "filename": db_resume.filename, "message": "upload successful"}


@router.get("/active")
def get_active_resume(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    resume = db.query(BaseResume).filter(
        BaseResume.user_id == current_user.id, BaseResume.is_active == True
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No active resume found. Please upload one first.")
    return resume


@router.post("/tailor")
async def tailor(
    resume_id: int,
    application_id: Optional[int] = None,
    job_description: Optional[str] = None,
    custom_instructions: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Resolve job description — prefer manually provided, fall back to application's
    app = None
    if application_id:
        app = db.query(Application).filter(
            Application.id == application_id, Application.user_id == current_user.id
        ).first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        if not job_description:
            job_description = app.job_description

    if not job_description:
        raise HTTPException(status_code=400, detail="Provide a job description or select an application")

    resume = db.query(BaseResume).filter(
        BaseResume.id == resume_id, BaseResume.user_id == current_user.id
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    tailored_html = await tailor_resume(resume.extracted_text, job_description, custom_instructions or "")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp_pdf_path = tmp.name

    # Use application_id or resume_id as the file identifier
    file_id = application_id or resume_id

    try:
        generate_pdf(tailored_html, tmp_pdf_path)
        if USE_S3:
            s3_key = f"generated/{current_user.id}/{file_id}_tailored.pdf"
            upload_file(tmp_pdf_path, s3_key)
            stored_path = s3_key
        else:
            local_path = os.path.join(GENERATED_DIR, f"{file_id}_tailored.pdf")
            os.replace(tmp_pdf_path, local_path)
            stored_path = local_path
    finally:
        if os.path.exists(tmp_pdf_path):
            os.unlink(tmp_pdf_path)

    if app:
        app.tailored_resume_path = stored_path
        db.commit()

    return {"message": "tailored", "download_url": f"/api/resume/download/{file_id}"}


@router.get("/download/{application_id}")
def download_resume(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not app or not app.tailored_resume_path:
        raise HTTPException(status_code=404, detail="Resume not found")

    if USE_S3:
        url = get_presigned_url(app.tailored_resume_path)
        return RedirectResponse(url)
    else:
        from fastapi.responses import FileResponse
        return FileResponse(app.tailored_resume_path, media_type="application/pdf", filename="tailored_resume.pdf")
