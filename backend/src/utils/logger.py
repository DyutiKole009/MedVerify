"""
Structured logging module for MedVerify backend.
Emits structured JSON logs containing correlation IDs (session_id, report_id, etc.).
"""
import logging
import json
import os
from typing import Any, Dict, Optional

class JSONFormatter(logging.Formatter):
    """Formats log records into structured JSON strings for CloudWatch Logs Insights."""
    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Merge extra context attributes if supplied
        if hasattr(record, "session_id"):
            log_entry["session_id"] = record.session_id
        if hasattr(record, "report_id"):
            log_entry["report_id"] = record.report_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "extra_data") and isinstance(record.extra_data, dict):
            log_entry.update(record.extra_data)
            
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)

def get_logger(name: str = "MedVerify") -> logging.Logger:
    """Returns a structured JSON logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        logger.setLevel(getattr(logging, log_level, logging.INFO))
    return logger

logger = get_logger("MedVerify")
