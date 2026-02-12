"""
Structured logging configuration
"""
import logging
import sys
from datetime import datetime


def setup_logger(name: str = "kalshi_bot", level: int = logging.INFO) -> logging.Logger:
    """
    Configure structured logging with console and file outputs
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Console handler - clean format
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '[%(asctime)s] %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)

    # File handler - detailed JSON-like format
    log_filename = f"kalshi_bot_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_filename)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}',
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )
    file_handler.setFormatter(file_format)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "kalshi_bot") -> logging.Logger:
    """Get or create logger"""
    return logging.getLogger(name)
