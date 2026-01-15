"""
Eccezioni custom per Selettore Rendimenti.
"""


class ScraperError(Exception):
    """Errore generico dello scraper."""
    pass


class RateLimitError(ScraperError):
    """Rate limit raggiunto dalla piattaforma."""
    pass


class DataNotFoundError(ScraperError):
    """Dati non trovati sulla piattaforma."""
    pass


class ConnectionError(ScraperError):
    """Errore di connessione alla piattaforma."""
    pass


class ValidationError(Exception):
    """Errore di validazione dati."""
    pass


class ExportError(Exception):
    """Errore durante l'export Excel."""
    pass
