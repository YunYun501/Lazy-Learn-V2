import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.lms_downloader import CourseMaterial, LMSDownloader


@pytest.fixture
def downloader():
    d = LMSDownloader()
    d._sessions = {}
    return d


def _make_mock_page(url: str = "https://lms.example.com/login"):
    page = AsyncMock()
    page.url = url
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    return page


def _make_mock_browser_stack(page):
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=page)
    browser = AsyncMock()
    browser.new_context = AsyncMock(return_value=context)
    pw = AsyncMock()
    chromium = MagicMock()
    chromium.launch = AsyncMock(return_value=browser)
    pw.chromium = chromium
    return pw, browser, context


@pytest.mark.asyncio
async def test_start_session_returns_session_id_and_waiting_status(downloader):
    page = _make_mock_page("https://lms.example.com/login")
    pw, browser, context = _make_mock_browser_stack(page)
    pw.start = AsyncMock(return_value=pw)

    with patch("app.services.lms_downloader.async_playwright") as mock_apl:
        mock_apl.return_value.start = AsyncMock(return_value=pw)
        result = await downloader.start_session("https://lms.example.com/login")

    assert "session_id" in result
    assert result["status"] == "waiting_for_login"
    assert len(result["session_id"]) == 36


@pytest.mark.asyncio
async def test_check_login_status_logged_in_when_url_changes(downloader):
    session_id = "test-session-123"
    page = _make_mock_page("https://lms.example.com/dashboard")

    from app.services.lms_downloader import _Session

    session = MagicMock(spec=_Session)
    session.lms_url = "https://lms.example.com/login"
    session.page = page
    session.created_at = asyncio.get_event_loop().time()
    downloader._sessions[session_id] = session

    status = await downloader.check_login_status(session_id)
    assert status == "logged_in"


@pytest.mark.asyncio
async def test_check_login_status_waiting_when_url_unchanged(downloader):
    session_id = "test-session-456"
    lms_url = "https://lms.example.com/login"
    page = _make_mock_page(lms_url)

    from app.services.lms_downloader import _Session

    session = MagicMock(spec=_Session)
    session.lms_url = lms_url
    session.page = page
    session.created_at = asyncio.get_event_loop().time()
    downloader._sessions[session_id] = session

    status = await downloader.check_login_status(session_id)
    assert status == "waiting"


@pytest.mark.asyncio
async def test_list_course_materials_parses_pdf_links(downloader):
    session_id = "test-session-789"
    course_url = "https://lms.example.com/course/1"

    page = _make_mock_page("https://lms.example.com/dashboard")
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.evaluate = AsyncMock(
        return_value=[
            {"href": "https://lms.example.com/files/lecture1.pdf", "text": "Lecture 1"},
            {"href": "https://lms.example.com/files/slides.pptx", "text": "Slides"},
            {"href": "https://lms.example.com/about", "text": "About"},
        ]
    )

    from app.services.lms_downloader import _Session

    session = MagicMock(spec=_Session)
    session.lms_url = "https://lms.example.com/login"
    session.page = page
    session.created_at = asyncio.get_event_loop().time()
    downloader._sessions[session_id] = session

    materials = await downloader.list_course_materials(session_id, course_url)

    assert len(materials) == 2
    assert all(isinstance(m, CourseMaterial) for m in materials)
    pdf_material = next(m for m in materials if m.file_type == "pdf")
    assert pdf_material.title == "Lecture 1"
    assert pdf_material.url == "https://lms.example.com/files/lecture1.pdf"
    pptx_material = next(m for m in materials if m.file_type == "pptx")
    assert pptx_material.title == "Slides"