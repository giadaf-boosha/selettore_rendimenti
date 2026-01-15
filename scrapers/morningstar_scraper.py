"""
Scraper per Morningstar via mstarpy.

Fonte primaria per fondi comuni e secondaria per ETF.
Supporta categorie Morningstar e fornisce dati di performance.
"""
import pandas as pd
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from scrapers.base import BaseDataSource, ProgressCallback
from core.models import (
    SourceRecord,
    SearchCriteria,
    PerformanceData,
    RiskMetrics,
    InstrumentType,
    DistributionPolicy,
)
from utils.retry import retry_with_backoff
from utils.validators import safe_float

logger = logging.getLogger(__name__)


class MorningstarScraper(BaseDataSource):
    """
    Scraper per Morningstar via mstarpy.

    Supporta sia ETF che Fondi comuni. Fornisce:
    - Categorie Morningstar
    - Performance (1a, 3a, 5a)
    - Deviazione standard
    - Rating Morningstar
    """

    def __init__(self):
        super().__init__(name="morningstar", rate_limit=0.5)
        self._mstarpy_available: Optional[bool] = None

    @property
    def supported_types(self) -> List[InstrumentType]:
        return [InstrumentType.ETF, InstrumentType.FUND]

    def _check_mstarpy(self) -> bool:
        """Verifica se mstarpy è disponibile."""
        if self._mstarpy_available is None:
            try:
                import mstarpy
                self._mstarpy_available = True
            except ImportError:
                self.logger.error("mstarpy not installed. Run: pip install mstarpy")
                self._mstarpy_available = False
        return self._mstarpy_available

    def _determine_instrument_type(self, security_type: str) -> InstrumentType:
        """Determina il tipo di strumento dalla stringa security type."""
        if not security_type:
            return InstrumentType.UNKNOWN

        sec_type_lower = str(security_type).lower()
        if "etf" in sec_type_lower:
            return InstrumentType.ETF
        elif "fund" in sec_type_lower or "fondo" in sec_type_lower:
            return InstrumentType.FUND
        return InstrumentType.UNKNOWN

    def _item_to_record(self, item: dict) -> Optional[SourceRecord]:
        """Converte risultato screener in SourceRecord."""
        isin = item.get("isin") or item.get("SecId")
        if not isin:
            return None

        # Determina tipo strumento
        sec_type = item.get("securityType", "") or item.get("LegalType", "")
        inst_type = self._determine_instrument_type(sec_type)

        return SourceRecord(
            isin=str(isin),
            name=str(item.get("name", "") or item.get("Name", "")),
            source=self.name,
            instrument_type=inst_type,
            currency=str(item.get("currency", "EUR") or item.get("BaseCurrencyId", "EUR")),
            category_morningstar=item.get("morningstarCategory") or item.get("CategoryName"),
            performance=PerformanceData(
                return_1y=safe_float(item.get("return1Year") or item.get("ReturnM12")),
                return_3y=safe_float(item.get("return3Year") or item.get("ReturnM36")),
                return_5y=safe_float(item.get("return5Year") or item.get("ReturnM60")),
            ),
            risk=RiskMetrics(
                volatility_3y=safe_float(
                    item.get("standardDeviation3Year") or item.get("StandardDeviation3Yr")
                ),
            ),
            raw_data=item,
        )

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def search(
        self,
        criteria: SearchCriteria,
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[SourceRecord]:
        """
        Cerca strumenti usando mstarpy.

        Nota: mstarpy ha funzionalità limitate per screening complesso.
        Implementiamo una ricerca base e filtriamo localmente.
        """
        if not self._check_mstarpy():
            self._update_progress(progress_callback, 1.0, "mstarpy non disponibile")
            return []

        self._update_progress(progress_callback, 0.1, "Ricerca su Morningstar...")

        records = []

        try:
            import mstarpy as ms

            # mstarpy non ha un vero screener, usiamo search
            # Cerchiamo per termini generici e poi filtriamo
            search_terms = []

            # Se ci sono categorie specificate, cerchiamo per categoria
            if criteria.categories_morningstar:
                search_terms.extend(criteria.categories_morningstar[:3])  # Limita a 3
            else:
                # Ricerca generica per tipo
                if InstrumentType.ETF in criteria.instrument_types:
                    search_terms.append("ETF")
                if InstrumentType.FUND in criteria.instrument_types:
                    search_terms.append("Fund")

            if not search_terms:
                search_terms = ["ETF", "Fund"]

            total_terms = len(search_terms)

            for idx, term in enumerate(search_terms):
                self._wait_rate_limit()

                try:
                    # Usa search_funds o search_stock a seconda del tipo
                    self._update_progress(
                        progress_callback,
                        0.1 + (0.7 * idx / total_terms),
                        f"Cercando: {term}..."
                    )

                    # Prova a cercare
                    results = ms.search_funds(term, page_size=100)

                    if results:
                        for item in results:
                            record = self._item_to_record(item)
                            if record and record.isin:
                                # Applica filtri
                                if self._matches_criteria(record, criteria):
                                    records.append(record)

                except Exception as e:
                    self.logger.warning(f"Search failed for '{term}': {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Morningstar search failed: {e}")

        # Deduplica per ISIN
        seen_isins = set()
        unique_records = []
        for record in records:
            if record.isin not in seen_isins:
                seen_isins.add(record.isin)
                unique_records.append(record)

        self._update_progress(
            progress_callback,
            1.0,
            f"Morningstar: {len(unique_records)} strumenti"
        )

        return unique_records

    def _matches_criteria(self, record: SourceRecord, criteria: SearchCriteria) -> bool:
        """Verifica se un record soddisfa i criteri."""
        # Filtro valuta
        if criteria.currencies and record.currency not in criteria.currencies:
            return False

        # Filtro tipo strumento
        if record.instrument_type not in criteria.instrument_types:
            if record.instrument_type != InstrumentType.UNKNOWN:
                return False

        # Filtro categoria Morningstar
        if criteria.categories_morningstar:
            if record.category_morningstar:
                # Match parziale sulla categoria
                cat_lower = record.category_morningstar.lower()
                if not any(c.lower() in cat_lower for c in criteria.categories_morningstar):
                    return False

        # Filtro performance minima
        if criteria.min_performance is not None:
            perf = record.performance.get_by_period(criteria.performance_period)
            if perf is None or perf < criteria.min_performance:
                return False

        return True

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def get_by_isin(self, isin: str) -> Optional[SourceRecord]:
        """Recupera dettagli per singolo ISIN."""
        if not self._check_mstarpy():
            return None

        self._wait_rate_limit()

        try:
            import mstarpy as ms

            # Prova prima come fondo
            try:
                fund = ms.Funds(isin)

                # Recupera NAV e info base
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=365 * 5)).strftime("%Y-%m-%d")

                nav_data = fund.nav(start_date=start_date, end_date=end_date)

                return SourceRecord(
                    isin=isin,
                    name=getattr(fund, "name", isin),
                    source=self.name,
                    instrument_type=InstrumentType.FUND,
                    currency="EUR",
                    performance=self._extract_performance_from_nav(nav_data),
                    raw_data={"nav": nav_data},
                )

            except Exception:
                pass

            # Prova come stock/ETF
            try:
                stock = ms.Stock(isin)
                hist = stock.historical(start_date=start_date, end_date=end_date)

                return SourceRecord(
                    isin=isin,
                    name=getattr(stock, "name", isin),
                    source=self.name,
                    instrument_type=InstrumentType.ETF,
                    currency="EUR",
                    raw_data={"historical": hist},
                )

            except Exception:
                pass

            return None

        except Exception as e:
            self.logger.error(f"Failed to get {isin} from Morningstar: {e}")
            return None

    def _extract_performance_from_nav(self, nav_data) -> PerformanceData:
        """Calcola performance da serie NAV."""
        perf = PerformanceData()

        if not nav_data:
            return perf

        try:
            # Se nav_data è una lista di dict con date e valori
            if isinstance(nav_data, list) and len(nav_data) > 1:
                # Ordina per data
                sorted_data = sorted(nav_data, key=lambda x: x.get("date", ""))

                if sorted_data:
                    start_val = float(sorted_data[0].get("nav", 0) or sorted_data[0].get("totalReturn", 0))
                    end_val = float(sorted_data[-1].get("nav", 0) or sorted_data[-1].get("totalReturn", 0))

                    if start_val > 0:
                        total_return = ((end_val - start_val) / start_val) * 100
                        # Questo è il return totale del periodo disponibile
                        perf.return_5y = round(total_return, 2)

        except Exception as e:
            self.logger.warning(f"Failed to extract performance from NAV: {e}")

        return perf

    def get_performance_history(
        self,
        isin: str,
        start_date: str,
        end_date: str
    ) -> Optional[dict]:
        """Recupera storico NAV."""
        if not self._check_mstarpy():
            return None

        try:
            import mstarpy as ms

            fund = ms.Funds(isin)
            nav_data = fund.nav(start_date=start_date, end_date=end_date)

            if nav_data:
                return {
                    "dates": [d.get("date") for d in nav_data if d.get("date")],
                    "values": [d.get("nav") for d in nav_data if d.get("nav")],
                    "total_return": [d.get("totalReturn") for d in nav_data if d.get("totalReturn")],
                }

        except Exception as e:
            self.logger.error(f"Failed to get NAV history for {isin}: {e}")

        return None

    def health_check(self) -> bool:
        """Verifica se mstarpy è funzionante."""
        if not self._check_mstarpy():
            return False

        try:
            import mstarpy as ms
            # Prova una ricerca semplice
            results = ms.search_funds("MSCI World", page_size=1)
            return True
        except Exception as e:
            self.logger.error(f"Morningstar health check failed: {e}")
            return False
