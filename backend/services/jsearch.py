import httpx
from config import settings

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"


async def search_job(role: str, location: str = "remote", page: int = 1):
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{ADZUNA_BASE_URL}/us/search/{page}"
        params = {
            "app_id": settings.adzuna_app_id,
            "app_key": settings.adzuna_app_key,
            "what": role,
            "where": location,
            "results_per_page": 20,
            "content-type": "application/json"
        }
        response = await client.get(url, params=params)
        return response.json()