"""
Configurazione logging per l'applicazione.
"""
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(
    level: str = "INFO",
    log_file: bool = True,
    log_dir: str = "logs",
    app_name: str = "selettore"
) -> logging.Logger:
    """
    Configura il logging per l'applicazione.

    Args:
        level: Livello logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Se True, scrive anche su file
        log_dir: Directory per file di log
        app_name: Nome applicazione per file log

    Returns:
        Root logger configurato
    """
    # Formato log
    fmt = "%(asctime)s | %(levelname)-8s | %(name)-20s | %(message)s"
    date_fmt = "%Y-%m-%d %H:%M:%S"

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Rimuovi handler esistenti
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(fmt, date_fmt))
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))
    root_logger.addHandler(console_handler)

    # File handler (opzionale)
    if log_file:
        try:
            log_path = Path(log_dir)
            log_path.mkdir(exist_ok=True)

            filename = log_path / f"{app_name}_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(filename, encoding="utf-8")
            file_handler.setFormatter(logging.Formatter(fmt, date_fmt))
            file_handler.setLevel(logging.DEBUG)  # File log sempre DEBUG
            root_logger.addHandler(file_handler)
        except Exception as e:
            root_logger.warning(f"Could not create log file: {e}")

    # Riduci verbosità librerie esterne
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Ottiene un logger con il nome specificato.

    Args:
        name: Nome del logger (tipicamente __name__)

    Returns:
        Logger configurato
    """
    return logging.getLogger(name)
