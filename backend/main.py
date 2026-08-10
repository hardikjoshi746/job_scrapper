import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routers import applications, jobs, resume, apply, auth
from database import Base, engine

app = FastAPI(title="Job Hunt Application")

ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000"
).split(",")

# Strip whitespace from each origin
ALLOWED_ORIGINS = [o.strip() for o in ALLOWED_ORIGINS]

# Allow all Vercel preview deployments matching *.vercel.app
ALLOWED_ORIGIN_REGEX = r"https://.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(resume.router, prefix="/api/resume", tags=["resume"])
app.include_router(apply.router, prefix="/api/apply", tags=["apply"])


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "backend is running"}
