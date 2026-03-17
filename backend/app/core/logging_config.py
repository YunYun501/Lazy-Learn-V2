"""Centralized logging configuration for Lazy Learn backend.

Provides:
- Structured JSON logs to rotating files (for machine parsing)
- Human-readable colored console output (for development)
- Per-module loggers via standard `logging.getLogger(__name__)`
- Configurable via LOG_LEVEL and LOG_DIR environment variables
"""

import logging
import logging.handlers
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Emit one JSON object per log line for easy parsing and search."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        # Capture ALL extra fields passed via logger.info(..., extra={...})
        standard_attrs = logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
        for key, val in record.__dict__.items():
            if key not in standard_attrs and key not in log_entry and val is not None:
                log_entry[key] = val

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """Colored, human-readable console output for development."""

    COLORS = {
        "DEBUG": "\033[36m",  # cyan
        "INFO": "\033[32m",  # green
        "WARNING": "\033[33m",  # yellow
        "ERROR": "\033[31m",  # red
        "CRITICAL": "\033[1;31m",  # bold red
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        timestamp = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
        name = record.name.replace("app.", "")

        prefix = f"{color}{timestamp} {record.levelname:<7}{self.RESET} [{name}]"
        message = record.getMessage()

        extras = []
        standard_attrs = logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
        for key, val in record.__dict__.items():
            if key not in standard_attrs and val is not None:
                extras.append(f"{key}={val}")
        if extras:
            message = f"{message}  ({', '.join(extras)})"

        formatted = f"{prefix} {message}"

        if record.exc_info and record.exc_info[0] is not None:
            formatted += "\n" + self.formatException(record.exc_info)

        return formatted


def setup_logging(log_level: str = "INFO", log_dir: str | Path = "data/logs") -> None:
    """Initialize logging for the entire application.

    Call once at startup (in main.py) before any other imports.

    Args:
        log_level: Root log level (DEBUG, INFO, WARNING, ERROR).
        log_dir: Directory for log files. Created automatically.
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    root.handlers.clear()

    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "app.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(JSONFormatter())
    file_handler.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_dir / "error.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setFormatter(JSONFormatter())
    error_handler.setLevel(logging.ERROR)
    root.addHandler(error_handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ConsoleFormatter())
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root.addHandler(console_handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    root_logger = logging.getLogger("app")
    root_logger.info(
        "Logging initialized — level=%s, log_dir=%s",
        log_level,
        log_dir.resolve(),
    )
