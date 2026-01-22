"""
Scraper per Investing.com via investiny.

NOTA: investpy non funziona più (bloccato da Cloudflare).
investiny è l'alternativa con funzionalità ridotte.

Usato principalmente per enrichment di ISIN specifici,
non per ricerche complesse.
"""
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from scrapers.base import BaseDataSource, ProgressCallback
from core.models import (
    SourceRecord,
    SearchCriteria,
    PerformanceData,
    InstrumentType,
)
from utils.retry import retry_with_backoff
from utils.validators import safe_float

logger = logging.getLogger(__name__)


class InvestinyScraper(BaseDataSource):
    """
    Scraper per Investing.com via investiny.

    LIMITAZIONI:
    - Non supporta ricerca per criteri complessi
    - Solo search_assets() e historical_data()
    - Usare principalmente per lookup ISIN specifici

    Funzionalità:
    - Ricerca asset per nome/ISIN
    - Storico prezzi giornaliero
    - Calcolo performance da storico
    """

    def __init__(self):
        # Rate limit increased to 2.0s to avoid triggering anti-bot measures
        super().__init__(name="investiny", rate_limit=2.0)
        self._investiny_available: Optional[bool] = None

    @property
    def supported_types(self) -> List[InstrumentType]:
        return [InstrumentType.FUND]  # Principalmente fondi

    def _check_investiny(self) -> bool:
        """Verifica se investiny è disponibile."""
        if self._investiny_available is None:
            try:
                from investiny import search_assets, historical_data
                self._investiny_available = True
            except ImportError:
                self.logger.error("investiny not installed. Run: pip install investiny")
                self._investiny_available = False
        return self._investiny_available

    def search(
        self,
        criteria: SearchCriteria,
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[SourceRecord]:
        """
        Investiny non supporta ricerca per criteri complessi.

        Restituisce lista vuota e logga warning.
        Usare get_by_isin() per lookup specifici.
        """
        self._update_progress(
            progress_callback,
            1.0,
            "Investiny: ricerca limitata, uso lookup ISIN"
        )

        self.logger.warning(
            "Investiny does not support complex searches. "
            "Use get_by_isin() for specific ISIN lookups."
        )

        return []

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def get_by_isin(self, isin: str) -> Optional[SourceRecord]:
        """
        Cerca strumento per ISIN su Investing.com.

        Args:
            isin: Codice ISIN da cercare

        Returns:
            SourceRecord o None se non trovato
        """
        if not self._check_investiny():
            return None

        self._wait_rate_limit()

        try:
            from investiny import search_assets, historical_data

            # Cerca per ISIN
            results = search_assets(query=isin, limit=5, type="Fund")

            if not results:
                # Prova come ETF
                results = search_assets(query=isin, limit=5, type="ETF")

            if not results:
                self.logger.debug(f"ISIN {isin} not found on Investiny")
                return None

            # Prendi il primo risultato
            best_match = results[0]
            investing_id = best_match.get("ticker") or best_match.get("id")

            if not investing_id:
                return None

            investing_id = int(investing_id)

            # Recupera dati storici per calcolare performance
            perf = self._calculate_performance(investing_id)

            return SourceRecord(
                isin=isin,
                name=str(best_match.get("name", "")),
                source=self.name,
                instrument_type=InstrumentType.FUND,
                currency=str(best_match.get("currency", "EUR")),
                performance=perf,
                raw_data={
                    "investing_id": investing_id,
                    "search_result": best_match,
                },
            )

        except Exception as e:
            self.logger.error(f"Failed to search {isin} on Investiny: {e}")
            return None

    def _calculate_performance(self, investing_id: int) -> PerformanceData:
        """
        Calcola performance da dati storici.

        Args:
            investing_id: ID Investing.com

        Returns:
            PerformanceData con performance calcolate
        """
        perf = PerformanceData()

        if not self._check_investiny():
            return perf

        try:
            from investiny import historical_data

            today = datetime.now()
            today_str = today.strftime("%m/%d/%Y")

            # Periodi da calcolare
            periods = {
                "return_1y": 365,
                "return_3y": 365 * 3,
                "return_5y": 365 * 5,
            }

            for attr, days in periods.items():
                try:
                    self._wait_rate_limit()

                    from_date = (today - timedelta(days=days)).strftime("%m/%d/%Y")

                    data = historical_data(
                        investing_id=investing_id,
                        from_date=from_date,
                        to_date=today_str
                    )

                    if data and len(data) > 1:
                        # Calcola rendimento percentuale
                        start_price = safe_float(data[0].get("close", 0))
                        end_price = safe_float(data[-1].get("close", 0))

                        if start_price and start_price > 0 and end_price:
                            ret = ((end_price - start_price) / start_price) * 100

                            # Annualizza se periodo > 1 anno
                            if days > 365:
                                years = days / 365
                                # CAGR formula
                                ret = ((1 + ret / 100) ** (1 / years) - 1) * 100

                            setattr(perf, attr, round(ret, 2))

                except Exception as e:
                    self.logger.warning(f"Failed to calculate {attr}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to calculate performance: {e}")

        return perf

    def get_performance_history(
        self,
        isin: str,
        start_date: str,
        end_date: str
    ) -> Optional[dict]:
        """
        Recupera storico prezzi.

        Args:
            isin: Codice ISIN
            start_date: Data inizio (YYYY-MM-DD)
            end_date: Data fine (YYYY-MM-DD)

        Returns:
            Dict con dates, close prices, volumes
        """
        if not self._check_investiny():
            return None

        try:
            from investiny import search_assets, historical_data

            # Prima trova l'investing_id
            results = search_assets(query=isin, limit=1)
            if not results:
                return None

            investing_id = int(results[0].get("ticker", 0) or results[0].get("id", 0))

            if not investing_id:
                return None

            # Converti formato date (YYYY-MM-DD -> MM/DD/YYYY)
            from_date = datetime.strptime(start_date, "%Y-%m-%d").strftime("%m/%d/%Y")
            to_date = datetime.strptime(end_date, "%Y-%m-%d").strftime("%m/%d/%Y")

            self._wait_rate_limit()

            data = historical_data(
                investing_id=investing_id,
                from_date=from_date,
                to_date=to_date
            )

            if not data:
                return None

            return {
                "dates": [d.get("date") for d in data if d.get("date")],
                "close": [safe_float(d.get("close")) for d in data],
                "volume": [safe_float(d.get("volume")) for d in data],
            }

        except Exception as e:
            self.logger.error(f"Failed to get history for {isin}: {e}")
            return None

    def health_check(self) -> bool:
        """Verifica se investiny è funzionante."""
        if not self._check_investiny():
            return False

        try:
            from investiny import search_assets

            # Prova una ricerca semplice
            results = search_assets(query="Apple", limit=1)
            return True

        except Exception as e:
            self.logger.error(f"Investiny health check failed: {e}")
            return False
