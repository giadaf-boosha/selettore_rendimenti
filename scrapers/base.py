"""
Classe base astratta per tutti i data source.

Definisce l'interfaccia comune che tutti gli scraper devono implementare.
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Callable
from time import time, sleep
import logging

from core.models import SourceRecord, SearchCriteria, InstrumentType


# Type alias per progress callback
ProgressCallback = Callable[[float, str], None]


class BaseDataSource(ABC):
    """
    Interfaccia astratta per tutti i data source.

    Pattern: Strategy + Template Method

    Tutti gli scraper (JustETF, Morningstar, Investiny) devono
    implementare questa interfaccia per garantire consistenza.
    """

    def __init__(self, name: str, rate_limit: float = 1.0):
        """
        Inizializza il data source.

        Args:
            name: Nome identificativo dello scraper
            rate_limit: Secondi minimi tra le richieste
        """
        self.name = name
        self.rate_limit = rate_limit
        self.logger = logging.getLogger(f"scraper.{name}")
        self._last_request_time: float = 0.0

    @property
    @abstractmethod
    def supported_types(self) -> List[InstrumentType]:
        """
        Tipi di strumenti supportati da questo scraper.

        Returns:
            Lista di InstrumentType supportati (ETF, FUND, o entrambi)
        """
        pass

    @abstractmethod
    def search(
        self,
        criteria: SearchCriteria,
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[SourceRecord]:
        """
        Cerca strumenti secondo i criteri specificati.

        Args:
            criteria: Criteri di ricerca (categorie, valute, ecc.)
            progress_callback: Callback per aggiornare progress bar (0.0-1.0, messaggio)

        Returns:
            Lista di SourceRecord trovati
        """
        pass

    @abstractmethod
    def get_by_isin(self, isin: str) -> Optional[SourceRecord]:
        """
        Recupera dati per un singolo ISIN.

        Args:
            isin: Codice ISIN (12 caratteri)

        Returns:
            SourceRecord o None se non trovato
        """
        pass

    def get_performance_history(
        self,
        isin: str,
        start_date: str,
        end_date: str
    ) -> Optional[dict]:
        """
        Recupera storico performance/NAV.

        Args:
            isin: Codice ISIN
            start_date: Data inizio (YYYY-MM-DD)
            end_date: Data fine (YYYY-MM-DD)

        Returns:
            Dict con date e valori, o None
        """
        # Implementazione di default: non supportato
        self.logger.warning(f"{self.name} does not support performance history")
        return None

    def health_check(self) -> bool:
        """
        Verifica se il servizio è raggiungibile.

        Returns:
            True se il servizio è disponibile
        """
        try:
            # Implementazione base: assume che sia disponibile
            return True
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    def _wait_rate_limit(self) -> None:
        """Attende per rispettare il rate limit."""
        elapsed = time() - self._last_request_time
        if elapsed < self.rate_limit:
            wait_time = self.rate_limit - elapsed
            self.logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            sleep(wait_time)
        self._last_request_time = time()

    def _update_progress(
        self,
        callback: Optional[ProgressCallback],
        progress: float,
        message: str
    ) -> None:
        """
        Helper per aggiornare progress callback in modo sicuro.

        Args:
            callback: Callback da chiamare (può essere None)
            progress: Valore progress 0.0-1.0
            message: Messaggio da mostrare
        """
        if callback:
            try:
                callback(min(1.0, max(0.0, progress)), message)
            except Exception as e:
                self.logger.warning(f"Progress callback failed: {e}")
