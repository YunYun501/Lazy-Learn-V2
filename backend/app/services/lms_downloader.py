"""LMS Downloader — Playwright-based Moodle course material downloads.

SECURITY: NEVER stores or auto-fills usernames/passwords.
Users must log in manually through the headed browser window.
Session cookies (login tokens) live in memory only for the session lifetime.
"""
from __future__ import annotations

import asyncio

import uuid
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright
from pydantic import BaseModel


SUPPORTED_EXTENSIONS = {".pdf", ".pptx", ".docx"}


class CourseMaterial(BaseModel):
    title: str
    url: str
    file_type: str
    size_bytes: Optional[int] = None


class DownloadResult(BaseModel):
    downloaded: list[str]
    failed: list[str]
    dest_dir: str



class _Session:
    """Internal session state. Does NOT store credentials."""

    def __init__(self, browser, context, page, lms_url: str):
        self.browser = browser
        self.context = context
        self.page = page
        self.lms_url = lms_url
        self.created_at = asyncio.get_event_loop().time()



class LMSDownloader:
    """Playwright-based downloader for Moodle-style LMS platforms.

    Design constraints:
    - NEVER auto-fill or store username/password.
    - Users authenticate manually in the headed Chromium window.
    - Session cookies (login tokens) live only in memory for the duration
      of the session.
    """

    _sessions: dict[str, _Session] = {}

    LOGIN_TIMEOUT_SECONDS: int = 300

    async def start_session(self, lms_url: str) -> dict:
        """Launch a headed Chromium browser, navigate to the LMS URL.

        Returns ``{session_id, status: "waiting_for_login"}``.
        The user must log in manually; credentials are NEVER stored.
        """


        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto(lms_url)

        session_id = str(uuid.uuid4())
        session = _Session(browser=browser, context=context, page=page, lms_url=lms_url)
        session._pw = pw  # type: ignore[attr-defined]
        self._sessions[session_id] = session

        return {"session_id": session_id, "status": "waiting_for_login"}

    async def check_login_status(self, session_id: str) -> str:
        """Poll whether the user has completed manual login.

        Returns:
            "waiting"   – still on the login page / original URL
            "logged_in" – URL has changed away from the initial LMS URL
            "timeout"   – session has exceeded LOGIN_TIMEOUT_SECONDS
            "not_found" – session_id is unknown
        """
        session = self._sessions.get(session_id)
        if session is None:
            return "not_found"

        elapsed = asyncio.get_event_loop().time() - session.created_at
        if elapsed > self.LOGIN_TIMEOUT_SECONDS:
            return "timeout"

        current_url = session.page.url
        if current_url != session.lms_url:
            return "logged_in"

        return "waiting"

    async def list_course_materials(
        self,
        session_id: str,
        course_url: str,
    ) -> list[CourseMaterial]:
        """Navigate to *course_url* and return links to PDF/PPTX/DOCX files.

        Scans all ``<a href>`` elements on the page and filters by extension.
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id!r} not found")

        await session.page.goto(course_url)
        await session.page.wait_for_load_state("networkidle")


        anchors = await session.page.evaluate(
            """() => {
                const links = [];
                document.querySelectorAll('a[href]').forEach(a => {
                    links.push({href: a.href, text: a.textContent.trim()});
                });
                return links;
            }"""
        )

        materials: list[CourseMaterial] = []
        seen_urls: set[str] = set()

        for anchor in anchors:
            href: str = anchor.get("href", "")
            text: str = anchor.get("text", "") or ""

            if not href or href in seen_urls:
                continue


            path_part = href.split("?")[0].lower()
            ext = Path(path_part).suffix
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            seen_urls.add(href)
            file_type = ext.lstrip(".")
            title = text.strip() or Path(path_part).stem

            materials.append(
                CourseMaterial(
                    title=title,
                    url=href,
                    file_type=file_type,
                )
            )

        return materials

    async def download_materials(
        self,
        session_id: str,
        material_urls: list[str],
        dest_dir: str,
    ) -> DownloadResult:
        """Download each URL using the authenticated browser session.

        Uses Playwright's download API so that session cookies are included
        automatically — no credential re-entry required.
        """
        session = self._sessions.get(session_id)
        if session is None:
            raise ValueError(f"Session {session_id!r} not found")

        dest_path = Path(dest_dir)
        dest_path.mkdir(parents=True, exist_ok=True)

        downloaded: list[str] = []
        failed: list[str] = []

        for url in material_urls:
            try:
                async with session.page.expect_download() as dl_info:
                    await session.page.evaluate(f"window.open({url!r}, '_blank')")
                download = await dl_info.value
                suggested = download.suggested_filename or Path(url.split("?")[0]).name
                save_path = dest_path / suggested
                await download.save_as(str(save_path))
                downloaded.append(str(save_path))
            except Exception:
                failed.append(url)

        return DownloadResult(
            downloaded=downloaded,
            failed=failed,
            dest_dir=str(dest_path),
        )

    async def close_session(self, session_id: str) -> None:
        """Close the Chromium browser and remove the session."""
        session = self._sessions.pop(session_id, None)
        if session is None:
            return
        try:
            await session.browser.close()
        except Exception:
            pass
        try:
            pw = getattr(session, "_pw", None)
            if pw is not None:
                await pw.stop()
        except Exception:
            pass


lms_downloader = LMSDownloader()
