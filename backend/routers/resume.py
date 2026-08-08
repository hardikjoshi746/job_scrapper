from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os, aiofiles
from dependencies import get_db
from models import BaseResume, Application
from services.resume_parser import extract_text
from services.claude import tailor_resume
from services.pdf_generator import generate_pdf

router = APIRouter()

UPLOAD_DIR = "uploads"
GENERATED_DIR = "generated"

@router.post("/upload")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(await file.read())
    extracted = extract_text(file_path)
    db.query(BaseResume).update({"is_active" : False})
    db_resume = BaseResume(
        filename=file.filename,
        file_path=file_path,
        extracted_text=extracted,
        is_active=True
    )
    db.add(db_resume)
    db.commit()
    db.refresh(db_resume)
    return {"resume_id" : db_resume.id, "filename" : db_resume.filename, "message" : "upload Successful"}

    

@router.get("/active")
def get_active_resume(db: Session = Depends(get_db)):
    resume = db.query(BaseResume).filter(BaseResume.is_active == True).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Active resume not found")
    return resume
    

@router.post("/tailor")
async def tailor(application_id: int, resume_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    resume = db.query(BaseResume).filter(BaseResume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    template_html = open("templates/resume.html").read()
    tailored_html = await tailor_resume(resume.extracted_text, app.job_description, template_html)
    pdf_path = generate_pdf(tailored_html, f"{GENERATED_DIR}/{application_id}_tailored.pdf")
    app.tailored_resume_path = pdf_path
    db.commit()
    db.refresh(app)
    return {"message": "tailored", "download_url": f"/api/resume/download/{application_id}"}



@router.get("/download/{application_id}")
def download_resume(application_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app or not app.tailored_resume_path:
        raise HTTPException(status_code=404, detail="Resume not found")
    return FileResponse(app.tailored_resume_path, media_type="application/pdf", filename="tailored_resume.pdf")