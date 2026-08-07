from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import applications, jobs
from database import Base, engine

app = FastAPI(title="Job hunt application")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"]
)
app.include_router(applications.router, prefix="/api/applications", tags=["applications"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.get("/")
def root():
    return {"message" : "backend is running"}