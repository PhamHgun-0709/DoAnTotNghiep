"""Logging configuration for Ad Analytics API."""

import logging
import logging.handlers
import os
from pathlib import Path
from datetime import datetime


def setup_logging(app_name: str = "ad-analytics") -> logging.Logger:
    """
    Setup centralized logging for the application.
    
    Creates logs in /workspace/logs/ directory
    """
    logs_dir = Path("/workspace/logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.DEBUG)
    
    # Console handler (INFO level)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)
    
    # File handler (DEBUG level)
    log_file = logs_dir / f"{app_name}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)
    
    return logger


# Get logger instance
logger = setup_logging("ad-analytics-api")
