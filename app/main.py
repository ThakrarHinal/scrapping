from fastapi import FastAPI, HTTPException
from app.scraper import capture_and_upload
from pydantic import BaseModel
import httpx
from app.scraper import capture_and_upload

app = FastAPI()

# Request Model
class ScraperRequest(BaseModel):
    url: str

@app.get("/")
def root():
    return {"message": "Scraper API is running!"}

@app.post("/scrape/")
async def scrape_and_upload(request: ScraperRequest):  # Accept JSON body
    try:
         async with httpx.AsyncClient(timeout=300) as client:  # Increase timeout
            uploaded_urls = capture_and_upload(request.url)
            return {"status": "success", "uploaded_files": uploaded_urls}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
