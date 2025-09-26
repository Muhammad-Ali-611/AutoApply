# automation.py
import asyncio
from playwright.async_api import async_playwright

async def play_apply(job_url: str, answers: dict, user_data_dir: str = "./.udata"):
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(user_data_dir, headless=False)
        page = await browser.new_page()
        logs = []

        try:
            await page.goto(job_url, wait_until="domcontentloaded", timeout=45000)
            logs.append(f"Opened {job_url}")

            # Example: handle a sign-in page if detected (site-specific)
            if await page.locator("text=Sign in").first.is_visible(timeout=2000):
                # Pause and let user complete login to avoid ToS issues
                logs.append("Sign-in required; awaiting manual login")
                await page.pause()  # You can guide the user in the UI
                logs.append("Resuming after manual login")

            # Site-specific selectors below; replace with adapters per site.
            if await page.locator("input[name='fullName']").count():
                await page.fill("input[name='fullName']", answers.get("name", ""))
            if await page.locator("input[type='email']").count():
                await page.fill("input[type='email']", answers.get("email", ""))
            if await page.locator("textarea[name='coverLetter']").count():
                await page.fill("textarea[name='coverLetter']", answers.get("cover_letter", ""))

            # Upload resume if field exists
            if await page.locator("input[type='file']").count():
                await page.set_input_files("input[type='file']", answers["resume_path"])
                logs.append("Uploaded resume")

            # Example submit
            if await page.locator("button:has-text('Submit')").count():
                await page.click("button:has-text('Submit')")
                logs.append("Clicked submit")

            await browser.close()
            return {"ok": True, "logs": logs}
        except Exception as e:
            logs.append(f"Error: {e}")
            await browser.close()
            return {"ok": False, "logs": logs}
