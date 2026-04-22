"""
Structured Logger Utility
Produces JSON-formatted log entries with timestamp, level, message, and metadata.
"""

import logging
import json
import os
import sys
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Custom log formatter that outputs each record as a JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Attach any extra fields that were passed via extra={}
        for key, val in record.__dict__.items():
            if key.startswith("extra_"):
                log_entry[key[6:]] = val  # strip "extra_" prefix

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logger(name: str, log_file: str, level: int = logging.DEBUG) -> logging.Logger:
    """
    Create and configure a named logger that writes JSON lines to both
    a rotating file and stdout.

    Args:
        name:     Logger name (appears in log entries).
        log_file: Relative or absolute path to the output log file.
        level:    Minimum logging level (default DEBUG).

    Returns:
        Configured logging.Logger instance.
    """
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(log_file) if os.path.dirname(log_file) else ".", exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers when reloading modules in development
    if logger.handlers:
        return logger

    formatter = JSONFormatter()

    # ── File handler ──────────────────────────────────────────────────────────
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # ── Console handler (plain text for readability) ───────────────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s  %(name)s – %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    return logger


def get_application_logger():
    """Convenience wrapper – returns the main application log."""
    from config import Config
    return setup_logger("application", Config.APP_LOG_FILE)


def get_security_logger():
    """Convenience wrapper – returns the dedicated security event log."""
    from config import Config
    return setup_logger("security", Config.SECURITY_LOG_FILE)
