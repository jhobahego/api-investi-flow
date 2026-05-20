import contextvars
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import settings

# Context variables for request tracking
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)
user_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "user_id", default=None
)


class ContextFilter(logging.Filter):
    """
    Logging filter that injects request_id and user_id from the contextvars
    into the log record.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get() or "-"
        record.user_id = user_id_var.get() or "-"
        return True


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for production logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "user_id": getattr(record, "user_id", None),
        }

        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Include extra fields if any are dynamically attached to record
        # ignoring standard LogRecord attributes
        standard_attrs = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "request_id",
            "user_id",
        }
        extra = {k: v for k, v in record.__dict__.items() if k not in standard_attrs}
        if extra:
            log_data["extra"] = extra

        return json.dumps(log_data)


class ConsoleFormatter(logging.Formatter):
    """
    Custom console formatter that formats request_id and user_id nicely for local development.
    """

    # Color definitions for console output
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[1;31m",  # Bold Red
        "RESET": "\033[0m",
    }

    def format(self, record: logging.LogRecord) -> str:
        # Pre-format request and user ids
        req_id = getattr(record, "request_id", "-")
        usr_id = getattr(record, "user_id", "-")

        # Colorize level name
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        level_colored = f"{color}{record.levelname:<8}{reset}"

        # Standard log prefix: timestamp - level - [logger] [Req: ...] [User: ...]
        asctime = self.formatTime(record, self.datefmt)
        prefix = (
            f"{asctime} - {level_colored} - [{record.name}] "
            f"[Req: \033[34m{req_id}\033[0m] [User: \033[35m{usr_id}\033[0m]"
        )

        message = record.getMessage()
        formatted_record = f"{prefix} - {message}"

        if record.exc_info:
            formatted_record += f"\n{self.formatException(record.exc_info)}"

        return formatted_record


def setup_logging() -> None:
    """
    Centralized logging configuration setup.
    Integrates application loggers and intercepts uvicorn/standard loggers.
    """
    log_level = settings.LOG_LEVEL.upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Clear root handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set base level
    root_logger.setLevel(numeric_level)

    # Stream handler for standard output (containers & terminal)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(numeric_level)

    # Context filter to inject contextvars
    context_filter = ContextFilter()
    stream_handler.addFilter(context_filter)

    # Select formatter based on ENVIRONMENT
    formatter: logging.Formatter
    if settings.ENVIRONMENT == "production":
        formatter = JsonFormatter()
    else:
        # Date format for readable logs: YYYY-MM-DD HH:MM:SS
        date_format = "%Y-%m-%d %H:%M:%S"
        formatter = ConsoleFormatter(datefmt=date_format)

    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # Intercept and route third-party/framework loggers through root logger handlers
    intercepted_loggers = [
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
        "sqlalchemy.engine",
        "fastapi",
    ]

    for logger_name in intercepted_loggers:
        logger = logging.getLogger(logger_name)
        # Clear existing handlers to prevent duplicate formatting or output
        logger.handlers = []
        logger.setLevel(numeric_level)
        logger.propagate = True
