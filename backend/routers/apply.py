from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dependencies import get_db, get_current_user
from models import Application, BaseResume, User

router = APIRouter()


@router.post("/{application_id}")
async def apply(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        from playwright.async_api import async_playwright
        from services.playwright_apply import Profile, autofill_wizard
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Auto-apply is only available when running locally."
        )

    app = db.query(Application).filter(
        Application.id == application_id, Application.user_id == current_user.id
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if not app.job_url:
        raise HTTPException(status_code=400, detail="No job URL on this application")

    resume = db.query(BaseResume).filter(
        BaseResume.user_id == current_user.id, BaseResume.is_active == True
    ).first()
    if not resume:
        raise HTTPException(status_code=404, detail="No active resume found")

    profile = Profile(
        resume_path=resume.file_path,
        values={
            "first_name": "Hardik",
            "last_name": "Joshi",
            "email": "joshi.hard@northeastern.edu",
            "phone": "857-200-9265",
            "city": "New York",
            "state": "NY",
            "country": "United States",
            "linkedin": "linkedin.com/in/Hardik-Joshi",
            "github": "github.com/hardikjoshi746",
        },
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="/Users/hardik/Library/Application Support/Google/Chrome",
            channel="chrome",
            headless=False,
            slow_mo=500,
        )
        page = await browser.new_page()
        await page.goto(app.job_url, wait_until="networkidle")
        reports = await autofill_wizard(page, profile)
        await browser.wait_for_event("disconnected", timeout=0)

    return {
        "ats": reports[0].ats,
        "steps": len(reports),
        "filled": sum(len(r.filled) for r in reports),
        "needs_user": sum(len(r.needs_user) for r in reports),
        "blocking": sum(len(r.blocking) for r in reports),
    }
