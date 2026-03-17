import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger("app.frontend")

router = APIRouter(prefix="/api/logs", tags=["logs"])


class FrontendLogEntry(BaseModel):
    level: str
    message: str
    context: Optional[str] = None
    component: Optional[str] = None
    error: Optional[str] = None
    stack: Optional[str] = None
    timestamp: Optional[str] = None
    session_id: Optional[str] = None


class FrontendLogBatch(BaseModel):
    entries: list[FrontendLogEntry]


LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warn": logging.WARNING,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}


@router.post("", status_code=204)
async def ingest_frontend_logs(batch: FrontendLogBatch, request: Request):
    client_ip = request.client.host if request.client else "unknown"

    for entry in batch.entries[:50]:
        level = LEVEL_MAP.get(entry.level.lower(), logging.INFO)
        extra = {"client_ip": client_ip}
        if entry.component:
            extra["component"] = entry.component
        if entry.context:
            extra["context"] = entry.context
        if entry.session_id:
            extra["session_id"] = entry.session_id

        msg = entry.message
        if entry.error:
            msg = f"{msg} | error={entry.error}"
        if entry.stack:
            msg = f"{msg}\n{entry.stack}"

        logger.log(level, "[FE] %s", msg, extra=extra)
