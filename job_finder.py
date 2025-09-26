# job_finder.py
import asyncio
import json
import re
from urllib.parse import urljoin

from playwright.async_api import async_playwright

# Default patterns (will be overridden dynamically from sources.json if provided)
ROLE_PAT = re.compile(r"\b(qa|quality|test|sdet|software\s+engineer)\b", re.I)
REMOTE_PAT = re.compile(r"\b(remote|work\s*from\s*home|anywhere)\b", re.I)
EXCLUDE_PAT = re.compile(r"\b(senior\s+director|vp|principal)\b", re.I)
ENTRY_PAT = re.compile(r"", re.I)  # empty means "no extra constraint"

def _compile_pattern(words: list[str], default_regex: str) -> re.Pattern:
    if not words:
        return re.compile(default_regex, re.I)
    parts = []
    for w in words:
        w = w.strip()
        if not w:
            continue
        parts.append(re.escape(w))
    if not parts:
        return re.compile(default_regex, re.I)
    alt = "|".join(parts)
    try:
        return re.compile(rf"\b({alt})\b", re.I)
    except re.error:
        return re.compile(alt, re.I)

def _apply_filters_from_cfg(cfg: dict) -> dict:
    global ROLE_PAT, REMOTE_PAT, EXCLUDE_PAT, ENTRY_PAT
    filters = cfg.get("filters", {}) or {}
    include_words = filters.get("include_keywords") or []
    remote_words = filters.get("remote_keywords") or []
    exclude_words = filters.get("exclude_keywords") or []
    entry_words = filters.get("entry_keywords") or []

    ROLE_PAT = _compile_pattern(include_words, r"\b(qa|quality|test|sdet|software\s+engineer)\b")
    REMOTE_PAT = _compile_pattern(remote_words, r"\b(remote|work\s*from\s*home|anywhere)\b")
    EXCLUDE_PAT = _compile_pattern(exclude_words, r"\b(senior\s+director|vp|principal)\b")
    # If entry_words provided, enforce at least one match; otherwise no constraint
    ENTRY_PAT = _compile_pattern(entry_words, r"")
    return {
        "has_remote_filter": bool(remote_words),
        "include_words": include_words,
        "remote_words": remote_words,
        "exclude_words": exclude_words,
    }

async def _fetch_json(page, url: str):
    resp = await page.request.get(url, timeout=45000)
    if not resp.ok:
        return None
    try:
        return await resp.json()
    except Exception:
        return None

def _match_role(title: str) -> bool:
    return bool(ROLE_PAT.search(title or ""))

def _match_remote(text: str) -> bool:
    return bool(REMOTE_PAT.search(text or ""))

def _excluded(text: str) -> bool:
    return bool(EXCLUDE_PAT.search(text or ""))

def _match_entry(title: str) -> bool:
    # If ENTRY_PAT is empty pattern, .pattern == "" => treat as "no constraint"
    if ENTRY_PAT.pattern == "":
        return True
    return bool(ENTRY_PAT.search(title or ""))

async def discover_lever(page, companies: list[str]) -> tuple[list[dict], dict]:
    jobs = []
    stats = {"lever_raw": 0, "lever_kept": 0}
    for company in companies:
        url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        data = await _fetch_json(page, url)
        if not data:
            continue
        stats["lever_raw"] += len(data)
        for j in data:
            title = j.get("text", "")
            loc = (j.get("categories", {}) or {}).get("location", "") or ""
            url = j.get("hostedUrl") or j.get("applyUrl") or ""
            company_name = j.get("categories", {}).get("team") or company
            text_to_check = f"{title} {loc}"
            if not _match_role(title):
                continue
            if not _match_remote(text_to_check):
                continue
            if _excluded(title):
                continue
            if not _match_entry(title):
                continue
            jobs.append({
                "title": title,
                "company": company_name,
                "url": url,
                "location": loc,
                "source": "lever",
            })
            stats["lever_kept"] += 1
    return jobs, stats

# ... existing code ...

async def discover_greenhouse(page, boards: list[str]) -> tuple[list[dict], dict]:
    jobs = []
    stats = {"gh_raw_links": 0, "gh_kept": 0}
    for board in boards:
        try:
            await page.goto(board, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            continue
        # Primary selector
        items = page.locator(".opening a")
        count = await items.count()
        # Fallbacks for boards that don't use .opening
        if count == 0:
            items = page.locator("section#jobs a[href*='/jobs/'], a[href*='/jobs/'][data-mapped], .jobs a[href*='/jobs/']")
            count = await items.count()
        stats["gh_raw_links"] += count
        for i in range(count):
            a = items.nth(i)
            title = (await a.text_content() or "").strip()
            href = await a.get_attribute("href")
            url = urljoin(board, href) if href else ""
            # Location heuristics: look for nearby node or data-attribute
            loc_node = a.locator("xpath=../following-sibling::*[1]")
            loc = (await loc_node.text_content() or "").strip()
            if not loc:
                loc_attr = await a.get_attribute("data-location")
                loc = (loc_attr or "").strip()
            text_to_check = f"{title} {loc}"
            if not _match_role(title):
                continue
            if not _match_remote(text_to_check):
                continue
            if _excluded(title):
                continue
            if not _match_entry(title):
                continue
            company_name = board.rstrip("/").split("/")[-1]
            jobs.append({
                "title": title,
                "company": company_name,
                "url": url,
                "location": loc,
                "source": "greenhouse",
            })
            stats["gh_kept"] += 1
    return jobs, stats

# NEW: Greenhouse API-based discovery for reliability
async def discover_greenhouse_api(page, boards: list[str]) -> tuple[list[dict], dict]:
    jobs = []
    stats = {"gh_api_raw": 0, "gh_api_kept": 0}

    def _slug_from_board(url: str) -> str:
        # Accept both bare slugs and full board URLs
        u = (url or "").strip().rstrip("/")
        if not u:
            return ""
        # If it's a URL, take the last path segment as slug
        if "://" in u:
            return u.split("/")[-1]
        return u  # already a slug

    for board in boards:
        slug = _slug_from_board(board)
        if not slug:
            continue
        api_url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
        data = await _fetch_json(page, api_url)
        if not data:
            continue
        items = data.get("jobs", []) or []
        stats["gh_api_raw"] += len(items)
        for j in items:
            title = (j.get("title") or "").strip()
            loc_obj = j.get("location") or {}
            loc = (loc_obj.get("name") or "").strip()
            url = j.get("absolute_url") or ""
            text_to_check = f"{title} {loc}"
            if not _match_role(title):
                continue
            if not _match_remote(text_to_check):
                continue
            if _excluded(title):
                continue
            if not _match_entry(title):
                continue
            company_name = slug
            jobs.append({
                "title": title,
                "company": company_name,
                "url": url,
                "location": loc,
                "source": "greenhouse_api",
            })
            stats["gh_api_kept"] += 1
    return jobs, stats

def dedupe(jobs: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for j in jobs:
        u = j.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(j)
    return out

async def _run_discovery(page, lever_companies, gh_boards) -> tuple[list[dict], dict]:
    lever_jobs, lever_stats = await discover_lever(page, lever_companies)
    # Prefer Greenhouse API; keep HTML fallback in case API is blocked
    gh_api_jobs, gh_api_stats = await discover_greenhouse_api(page, gh_boards)
    gh_html_jobs, gh_html_stats = await discover_greenhouse(page, gh_boards) if gh_api_stats.get("gh_api_raw", 0) == 0 else ([], {"gh_raw_links": 0, "gh_kept": 0})

    all_jobs = dedupe(lever_jobs + gh_api_jobs + gh_html_jobs)
    stats = {
        **lever_stats,
        **gh_api_stats,
        **gh_html_stats,
        "total_after_dedupe": len(all_jobs),
    }
    return all_jobs, stats

async def find_jobs(sources_path: str = "sources.json", max_total: int = 10) -> list[dict]:
    # Load config and apply dynamic filters
    with open(sources_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    filter_info = _apply_filters_from_cfg(cfg)

    lever_companies = cfg.get("lever_companies", [])
    gh_boards = cfg.get("greenhouse_boards", [])

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        jobs, stats = await _run_discovery(page, lever_companies, gh_boards)

        # If nothing found, automatically retry without remote filter (common cause)
        if len(jobs) == 0 and filter_info.get("has_remote_filter"):
            print("No jobs matched with remote filter; retrying without remote constraint to diagnose…")
            global REMOTE_PAT
            REMOTE_PAT = re.compile(r".*", re.I)
            jobs, stats = await _run_discovery(page, lever_companies, gh_boards)
            if stats.get("total_after_dedupe", 0) > 0:
                print(f"Found {stats['total_after_dedupe']} jobs without remote filter. "
                      f"Consider broadening filters.remote_keywords in sources.json (currently: {filter_info.get('remote_words')}).")

        # Diagnostics
        print(f"Lever: raw={stats.get('lever_raw',0)} kept={stats.get('lever_kept',0)} | "
              f"Greenhouse API: raw={stats.get('gh_api_raw',0)} kept={stats.get('gh_api_kept',0)} | "
              f"Greenhouse HTML: raw_links={stats.get('gh_raw_links',0)} kept={stats.get('gh_kept',0)} | "
              f"Total (deduped)={stats.get('total_after_dedupe',0)}")

        await browser.close()

    return jobs[:max_total]