"""Structured, rotating, secret-redacting logging configuration."""
from __future__ import annotations
import logging
import logging.handlers
from pathlib import Path
from app.config import config
from app.services.launch_hardening import redact_log_line
class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact_log_line(super().format(record))
def setup_logging() -> None:
    logs_dir: Path = config.logs_dir
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "app.log"
    formatter = RedactingFormatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S")
    console = logging.StreamHandler(); console.setLevel(logging.INFO); console.setFormatter(formatter)
    file_handler = logging.handlers.RotatingFileHandler(str(log_file), maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG); file_handler.setFormatter(formatter)
    root = logging.getLogger(); root.setLevel(logging.DEBUG)
    for handler in list(root.handlers): root.removeHandler(handler); handler.close()
    root.addHandler(console); root.addHandler(file_handler)
def get_logger(name: str) -> logging.Logger: return logging.getLogger(name)
