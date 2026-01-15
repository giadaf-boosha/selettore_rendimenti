"""
Funzioni di validazione per dati finanziari.
"""
import re
from typing import Optional
from decimal import Decimal


# Pattern ISIN: 2 lettere paese + 9 alfanumerici + 1 check digit numerico
ISIN_PATTERN = re.compile(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')

# Range performance ragionevoli
PERF_MIN = -99.99
PERF_MAX = 1000.0


def validate_isin(isin: str) -> bool:
    """
    Valida il formato di un codice ISIN.

    Args:
        isin: Codice ISIN da validare (12 caratteri)

    Returns:
        True se il formato è valido, False altrimenti
    """
    if not isin or len(isin) != 12:
        return False
    return bool(ISIN_PATTERN.match(isin.upper()))


def validate_performance_range(value: Optional[float]) -> bool:
    """
    Valida che una performance sia in un range ragionevole.

    Args:
        value: Valore performance in percentuale

    Returns:
        True se il valore è nel range ragionevole
    """
    if value is None:
        return True
    return PERF_MIN <= value <= PERF_MAX


def normalize_isin(isin: str) -> str:
    """
    Normalizza un codice ISIN (uppercase, trim).

    Args:
        isin: Codice ISIN da normalizzare

    Returns:
        ISIN normalizzato
    """
    if not isin:
        return ""
    return isin.strip().upper()


def normalize_currency(currency: str) -> str:
    """
    Normalizza un codice valuta (uppercase, 3 caratteri).

    Args:
        currency: Codice valuta da normalizzare

    Returns:
        Valuta normalizzata o "EUR" come default
    """
    if not currency:
        return "EUR"
    normalized = currency.strip().upper()[:3]
    return normalized if len(normalized) == 3 else "EUR"


def safe_float(value, default: Optional[float] = None) -> Optional[float]:
    """
    Converte un valore a float in modo sicuro.

    Args:
        value: Valore da convertire
        default: Valore di default se la conversione fallisce

    Returns:
        Float o default
    """
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_decimal(value, default: Optional[Decimal] = None) -> Optional[Decimal]:
    """
    Converte un valore a Decimal in modo sicuro.

    Args:
        value: Valore da convertire
        default: Valore di default se la conversione fallisce

    Returns:
        Decimal o default
    """
    if value is None:
        return default
    try:
        return Decimal(str(value))
    except Exception:
        return default
