#!/usr/bin/env python3
"""
Centralized logging configuration for Career Forge.
Provides structured logging with timestamps and log levels.
"""

import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

# Configure default log level from environment or use INFO
DEFAULT_LOG_LEVEL = logging.INFO


class StructuredFormatter(logging.Formatter):
    """Custom formatter that adds structured information to log messages."""

    def format(self, record: logging.LogRecord) -> str:
        # Add timestamp
        record.timestamp = datetime.utcnow().isoformat()

        # Format the message
        if hasattr(record, 'event_data'):
            # Structured event logging
            event_str = f" | {record.event_data}" if record.event_data else ""
            return f"{record.timestamp} [{record.levelname}] {record.name}: {record.getMessage()}{event_str}"
        else:
            # Standard logging
            return f"{record.timestamp} [{record.levelname}] {record.name}: {record.getMessage()}"


def setup_logger(name: str, level: int = DEFAULT_LOG_LEVEL) -> logging.Logger:
    """
    Set up a logger with standardized configuration.

    Args:
        name: Logger name (typically __name__ from calling module)
        level: Logging level (default: INFO)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if logger already configured
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(StructuredFormatter())

    logger.addHandler(handler)

    return logger


def log_event(logger: logging.Logger, level: str, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
    """
    Log a structured event with optional data.

    Args:
        logger: Logger instance
        level: Log level ('debug', 'info', 'warning', 'error', 'critical')
        event_type: Type of event being logged
        data: Optional dictionary of additional data
    """
    log_func = getattr(logger, level.lower())

    # Create extra dict for structured data
    extra = {'event_data': data if data else {}}

    log_func(event_type, extra=extra)


# Convenience function for quick logger setup
def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    return setup_logger(name)
