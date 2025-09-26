# run_auto_apply.py
import argparse
import asyncio
import json
import os
import random
import time

from playwright.async_api import async_playwright

from apply_runner import apply_to_job
from job_finder import find_jobs

def read_json(path):
    search = [path]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(path):
        search.append(os.path.join(script_dir, path))
    last_err = None
    for candidate in search:
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError as e:
            last_err = e
            continue
    raise FileNotFoundError(f"Could not find JSON file. Tried: {', '.join(search)}") from last_err

async def extract_job_desc(url: str, max_chars: int = 6000) -> str:
    # Light-weight description grab via Playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            # Take the visible text; ATS pages usually work fine with body text
            text = await page.text_content("body")
            text = (text or "").strip()
            return text[:max_chars]
        except Exception:
            return ""
        finally:
            await browser.close()

async def main():
    parser = argparse.ArgumentParser(description="Auto-find and apply to QA/Software Engineer remote jobs.")
    parser.add_argument("--applicant", default="application.json")
    parser.add_argument("--resume", default="base_resume.json")
    parser.add_argument("--sources", default="sources.json")
    parser.add_argument("--max", type=int, default=3, help="Max applications per run")
    parser.add_argument("--delay-min", type=float, default=8.0, help="Min delay seconds between applications")
    parser.add_argument("--delay-max", type=float, default=20.0, help="Max delay seconds between applications")
    args = parser.parse_args()

    applicant = read_json(args.applicant)
    base_resume = read_json(args.resume)

    jobs = await find_jobs(args.sources, max_total=args.max * 3)
    if not jobs:
        print("No jobs discovered. Adjust sources.json.")
        return

    applied = 0
    for job in jobs:
        if applied >= args.max:
            break

        url = job["url"]
        company = job.get("company", "")
        role = job.get("title", "")

        jd = await extract_job_desc(url)
        # Optional:ensure role still looks relevant withdescription present
        if not jd:
            # skip postings that block content scraping without Login
            continue

        print(f"Applying to: {company} — {role} — {url}")

        result = await apply_to_job(
            job_url=url,
            applicant=applicant,
            base_resume=base_resume,
            job_meta={"company": company, "role": role, "job_desc": jd}
        )
        print(result)

        applied += 1
        # Randomized delay between applications
        d = random.uniform(args.delay_min, args.delay_max)
        await asyncio.sleep(d)

if __name__ == "__main__":
    asyncio.run(main())