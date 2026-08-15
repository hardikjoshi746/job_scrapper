import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from routers import applications, jobs, resume, apply, auth, scraper
from services.security import get_user_key
from database import Base, engine

limiter = Limiter(key_func=get_user_key)

app = FastAPI(title="Job Hunt Application", redirect_slashes=False)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(resume.router, prefix="/api/resume", tags=["resume"])
app.include_router(apply.router, prefix="/api/apply", tags=["apply"])
app.include_router(scraper.router, prefix="/api/scraper", tags=["scraper"])


@app.on_event("startup")
def startup():
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


@app.get("/")
def root():
    return {"message": "backend is running"}
