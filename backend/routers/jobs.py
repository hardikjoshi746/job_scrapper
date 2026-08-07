from fastapi import APIRouter
from services.jsearch import search_job

router = APIRouter()

@router.get("/search")
async def search(role: str, location: str = "remote", page: int = 1):
    return await search_job(role, location, page)