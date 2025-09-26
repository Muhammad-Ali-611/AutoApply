# fastapi_app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import Optional
import asyncio

app = FastAPI()

class Job(BaseModel):
    title: str
    company: str
    url: HttpUrl
    description: str
    location: Optional[str] = None

class ApplyRequest(BaseModel):
    job_url: HttpUrl
    resume_text: str
    cover_prompt: Optional[str] = None
    dry_run: bool = True

@app.post("/jobs/score")
def score_job(job: Job):
    # Very naive keyword scoring
    desired = {"python", "api", "backend", "fastapi", "playwright"}
    text = (job.title + " " + job.company + " " + job.description).lower()
    score = sum(1 for k in desired if k in text) / max(1, len(desired))
    return {"score": score}

@app.post("/apply")
async def apply_job(req: ApplyRequest):
    # Kick off an async automation task
    try:
        result = await run_application(job_url=req.job_url, resume_text=req.resume_text, cover_prompt=req.cover_prompt, dry_run=req.dry_run)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def run_application(job_url: str, resume_text: str, cover_prompt: Optional[str], dry_run: bool):
    # Stub: call your Playwright routine; return logs instead when dry_run=True
    if dry_run:
        return {"message": "Dry run; would open job page and fill forms.", "url": job_url}
    # In production: call automation.play_apply(...)
    return {"message": "Submitted (simulated).", "url": job_url}