# ats_adapters.py
from typing import Dict, Optional
from playwright.async_api import Page

class ATSAdapter:
    name = "base"
    def matches(self, url: str) -> bool:
        raise NotImplementedError
    async def login_if_needed(self, page: Page) -> None:
        # Implement site-specific login or detect login state
        return
    async def fill_and_submit(self, page: Page, applicant: Dict[str, str], docs: Dict[str, str]) -> Dict[str, str]:
        raise NotImplementedError

class GreenhouseAdapter(ATSAdapter):
    name = "greenhouse"
    def matches(self, url: str) -> bool:
        return "greenhouse.io" in url

    async def fill_and_submit(self, page: Page, applicant: Dict[str, str], docs: Dict[str, str]) -> Dict[str, str]:
        logs = []
        # Basic pattern on GH hosted forms
        if await page.locator("input[name='first_name']").count():
            await page.fill("input[name='first_name']", applicant.get("first_name", ""))
            await page.fill("input[name='last_name']", applicant.get("last_name", ""))
        if await page.locator("input[type='email']").count():
            await page.fill("input[type='email']", applicant.get("email", ""))
        if await page.locator("input[type='tel']").count():
            await page.fill("input[type='tel']", applicant.get("phone", ""))
        if await page.locator("textarea[name*='cover']").count():
            await page.fill("textarea[name*='cover']", docs.get("cover_letter_text", ""))

        # Upload resume
        if await page.locator("input[type='file']").count():
            await page.set_input_files("input[type='file']", docs["resume_path"])
            logs.append("Uploaded resume")

        # Submit
        if await page.locator("button[type='submit']").count():
            await page.click("button[type='submit']")
            logs.append("Submitted application")
        return {"ok": True, "logs": logs}

class LeverAdapter(ATSAdapter):
    name = "lever"
    def matches(self, url: str) -> bool:
        return "jobs.lever.co" in url

    async def fill_and_submit(self, page: Page, applicant: Dict[str, str], docs: Dict[str, str]) -> Dict[str, str]:
        logs = []
        # Lever fields are often standardized
        if await page.locator("input[name='name']").count():
            await page.fill("input[name='name']", applicant.get("full_name", ""))
        if await page.locator("input[name='email']").count():
            await page.fill("input[name='email']", applicant.get("email", ""))
        if await page.locator("input[name='phone']").count():
            await page.fill("input[name='phone']", applicant.get("phone", ""))
        if await page.locator("textarea[name='comments']").count():
            await page.fill("textarea[name='comments']", docs.get("cover_letter_text", ""))

        if await page.locator("input[type='file']").count():
            await page.set_input_files("input[type='file']", docs["resume_path"])
            logs.append("Uploaded resume")

        if await page.locator("button:has-text('Submit')").count():
            await page.click("button:has-text('Submit')")
            logs.append("Submitted application")
        return {"ok": True, "logs": logs}

class WorkdayAdapter(ATSAdapter):
    name = "workday"
    def matches(self, url: str) -> bool:
        return "workday" in url

    async def login_if_needed(self, page: Page) -> None:
        # Many Workday instances require account + flow steps
        # Detect login form; if present, you may need a credentials vault
        return

    async def fill_and_submit(self, page: Page, applicant: Dict[str, str], docs: Dict[str, str]) -> Dict[str, str]:
        logs = []
        # Workday flows differ by tenant; keep robust queries and fallbacks
        # Resume upload first
        if await page.locator("input[type='file']").count():
            await page.set_input_files("input[type='file']", docs["resume_path"])
            logs.append("Uploaded resume")

        # Basic personal info
        for sel, val in [
            ("input[aria-label='First Name']", applicant.get("first_name", "")),
            ("input[aria-label='Last Name']", applicant.get("last_name", "")),
            ("input[aria-label='Email']", applicant.get("email", "")),
            ("input[aria-label='Phone']", applicant.get("phone", "")),
        ]:
            if await page.locator(sel).count():
                await page.fill(sel, val)

        # Cover letter textarea (if exists)
        if await page.locator("textarea").filter(has_text="Cover Letter").count():
            el = page.locator("textarea").filter(has_text="Cover Letter").first
            await el.fill(docs.get("cover_letter_text", ""))

        # Continue/Submit buttons often vary
        for label in ["Submit", "Apply", "Next", "Review"]:
            if await page.locator(f"button:has-text('{label}')").count():
                await page.click(f"button:has-text('{label}')")
                logs.append(f"Clicked {label}")
        return {"ok": True, "logs": logs}

ADAPTERS = [GreenhouseAdapter(), LeverAdapter(), WorkdayAdapter()]

def pick_adapter(url: str) -> Optional[ATSAdapter]:
    for a in ADAPTERS:
        if a.matches(url):
            return a
    return None