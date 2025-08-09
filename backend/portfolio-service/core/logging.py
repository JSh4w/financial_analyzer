"Handles logging configuration for project"
import logging.config
from typing import Dict, Any

def setup_logging(level: str = "INFO") -> None:
    """Initialize logging configuration"""
    log_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": "default",
            },
        },
        "root": {"level": level, "handlers": ["console"]},
    }

    #Sets logging configuration across files
    logging.config.dictConfig(log_config)
    