"""Structured logging configuration shared by integration entry points."""

from __future__ import annotations

import os

import structlog


def configure_logging() -> None:
    """Configure console logs, or JSON logs when requested by the runtime."""
    log_format = os.getenv("OBLIDOG_LOG_FORMAT", "console")
    if log_format == "console":
        renderer = structlog.dev.ConsoleRenderer()
    elif log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        raise ValueError("OBLIDOG_LOG_FORMAT must be either 'console' or 'json'")

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
