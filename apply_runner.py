# apply_runner.py
import asyncio, tempfile, os
from typing import Dict
from playwright.async_api import async_playwright
from ats_adapters import pick_adapter
from tailoring import generate_application_package

async def apply_to_job(job_url: str, applicant: Dict[str, str], base_resume: Dict, job_meta: Dict[str, str]):
    package = generate_application_package(applicant, base_resume, job_meta)

    # Write tailored resume to a temporary .txt file for upload
    # (Switch to PDF later if desired)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as f:
        f.write(package["resume_text"].encode("utf-8"))
        resume_path = f.name

    docs = {
        "resume_path": resume_path,
        "cover_letter_text": package["cover_letter_text"],
    }

    adapter = pick_adapter(job_url)
    if not adapter:
        return {"ok": False, "error": "No ATS adapter found for URL."}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        logs = []
        try:
            await page.goto(job_url, wait_until="domcontentloaded", timeout=60000)
            if hasattr(adapter, "login_if_needed"):
                await adapter.login_if_needed(page)
            result = await adapter.fill_and_submit(page, applicant, docs)
            logs.extend(result.get("logs", []))
            await browser.close()
            return {"ok": result.get("ok", False), "logs": logs}
        finally:
            await browser.close()
            try:
                os.unlink(resume_path)
            except Exception:
                pass

# Example usage:
# asyncio.run(apply_to_job(job_url, applicant_dict, base_resume_dict, {"company": "Acme", "role": "Backend Engineer", "job_desc": jd_text}))