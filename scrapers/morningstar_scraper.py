"""
Scraper per Morningstar via mstarpy.

Fonte primaria per fondi comuni e secondaria per ETF.
Supporta categorie Morningstar e fornisce dati di performance.
"""
from typing import List, Optional
import logging
import re

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

# Pattern per validazione ISIN
ISIN_PATTERN = re.compile(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')


class MorningstarScraper(BaseDataSource):
    """
    Scraper per Morningstar via mstarpy.

    Supporta sia ETF che Fondi comuni. Fornisce:
    - Categorie Morningstar
    - Performance (YTD, 1a, 3a, 5a, 10a)
    - Volatility e Sharpe ratio
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
                import mstarpy.funds
                import mstarpy.search
                self._mstarpy_available = True
            except ImportError:
                self.logger.error("mstarpy not installed. Run: pip install mstarpy")
                self._mstarpy_available = False
        return self._mstarpy_available

    def _validate_isin(self, isin: str) -> bool:
        """Valida il formato ISIN."""
        if not isin or len(isin) != 12:
            return False
        return bool(ISIN_PATTERN.match(isin.upper()))

    def _extract_isin_from_meta(self, meta: dict) -> Optional[str]:
        """
        Estrae l'ISIN reale dai metadati Morningstar.

        Morningstar può restituire securityID (identificatore interno)
        invece dell'ISIN. Cerchiamo l'ISIN nei vari campi possibili.
        """
        # Campi dove potrebbe trovarsi l'ISIN
        isin_fields = ["isin", "Isin", "ISIN", "isinCode", "IsinCode"]

        for field in isin_fields:
            if field in meta and meta[field]:
                isin = str(meta[field]).strip().upper()
                if self._validate_isin(isin):
                    return isin

        # Se non troviamo ISIN nei campi specifici, verifica se securityID è un ISIN valido
        sec_id = meta.get("securityID", "")
        if sec_id:
            sec_id_upper = str(sec_id).strip().upper()
            if self._validate_isin(sec_id_upper):
                return sec_id_upper

        return None

    def _determine_instrument_type(self, investment_type: str) -> InstrumentType:
        """Determina il tipo di strumento dalla stringa investment type."""
        if not investment_type:
            return InstrumentType.UNKNOWN

        inv_type_lower = str(investment_type).lower()
        if inv_type_lower in ("et", "etf"):
            return InstrumentType.ETF
        elif inv_type_lower in ("fo", "fund", "fc", "fe"):
            return InstrumentType.FUND
        return InstrumentType.UNKNOWN

    def _extract_performance_from_trailing(
        self, trailing_data: dict, column_defs: list
    ) -> PerformanceData:
        """Estrae PerformanceData da trailingReturn()."""
        perf = PerformanceData()

        if not trailing_data or not column_defs:
            return perf

        # Mappa colonne a valori
        col_to_val = dict(zip(column_defs, trailing_data))

        perf.ytd = safe_float(col_to_val.get("YearToDate"))
        perf.return_1y = safe_float(col_to_val.get("1Year"))
        perf.return_3y = safe_float(col_to_val.get("3Year"))
        perf.return_5y = safe_float(col_to_val.get("5Year"))
        perf.return_10y = safe_float(col_to_val.get("10Year"))

        return perf

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def search(
        self,
        criteria: SearchCriteria,
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[SourceRecord]:
        """
        Cerca strumenti usando mstarpy screener_universe.

        Nota importante: L'API Morningstar (mstarpy v8) restituisce solo
        securityID interni nelle ricerche di massa, NON codici ISIN validi.
        Per ottenere l'ISIN reale è necessario chiamare Funds(id).snapshot()
        per ogni strumento, il che è troppo lento per ricerche di massa.

        Questa implementazione filtra per ISIN validi e quindi potrebbe
        restituire pochi o nessun risultato. Usare get_by_isin() per
        lookup specifici con ISIN noti.
        """
        if not self._check_mstarpy():
            self._update_progress(progress_callback, 1.0, "mstarpy non disponibile")
            return []

        self._update_progress(progress_callback, 0.1, "Ricerca su Morningstar...")

        records = []

        try:
            import mstarpy.search as ms_search

            # Cerca ETF e/o fondi
            search_types = []
            if InstrumentType.ETF in criteria.instrument_types:
                search_types.append("etf")
            if InstrumentType.FUND in criteria.instrument_types:
                search_types.append("fund")

            if not search_types:
                search_types = ["etf", "fund"]

            total_types = len(search_types)

            for idx, asset_type in enumerate(search_types):
                self._wait_rate_limit()

                self._update_progress(
                    progress_callback,
                    0.1 + (0.6 * idx / total_types),
                    f"Cercando {asset_type}..."
                )

                try:
                    # screener_universe restituisce metadati base
                    results = ms_search.screener_universe(
                        term=asset_type,
                        pageSize=200,  # Limita risultati
                    )

                    if results:
                        # Per ogni risultato, estrai ISIN valido
                        skipped_count = 0
                        for item in results:
                            meta = item.get("meta", {})

                            # Estrai ISIN reale (non securityID interno)
                            isin = self._extract_isin_from_meta(meta)

                            if isin:
                                # Solo record con ISIN valido
                                record = SourceRecord(
                                    isin=isin,
                                    name=meta.get("name", ""),
                                    source=self.name,
                                    instrument_type=self._determine_instrument_type(asset_type),
                                    raw_data=meta,
                                )
                                records.append(record)
                            else:
                                skipped_count += 1

                        if skipped_count > 0:
                            self.logger.debug(f"Skipped {skipped_count} records without valid ISIN")

                except Exception as e:
                    self.logger.warning(f"Search failed for '{asset_type}': {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Morningstar search failed: {e}")

        self._update_progress(
            progress_callback,
            1.0,
            f"Morningstar: {len(records)} strumenti trovati"
        )

        return records

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def get_by_isin(self, isin: str) -> Optional[SourceRecord]:
        """Recupera dettagli per singolo ISIN."""
        if not self._check_mstarpy():
            return None

        self._wait_rate_limit()

        try:
            import mstarpy.funds as ms_funds

            # Crea oggetto Funds con ISIN
            fund = ms_funds.Funds(isin)

            # Recupera snapshot per info base
            snapshot = {}
            try:
                snapshot = fund.snapshot() or {}
            except Exception as e:
                self.logger.debug(f"snapshot() failed for {isin}: {e}")

            # Recupera trailing returns per performance e categoria
            trailing = {}
            category = None
            perf = PerformanceData()

            try:
                trailing = fund.trailingReturn() or {}
                column_defs = trailing.get("columnDefs", [])
                total_return = trailing.get("totalReturnNAV", [])

                perf = self._extract_performance_from_trailing(total_return, column_defs)
                category = trailing.get("categoryName")
            except Exception as e:
                self.logger.debug(f"trailingReturn() failed for {isin}: {e}")

            # Se non abbiamo category da trailing, prova riskVolatility
            if not category:
                try:
                    risk_data = fund.riskVolatility() or {}
                    category = risk_data.get("categoryName")
                except Exception as e:
                    self.logger.debug(f"riskVolatility() failed for {isin}: {e}")

            # Determina tipo strumento
            inv_type = snapshot.get("InvestmentType", "")
            instrument_type = self._determine_instrument_type(inv_type)

            # Determina distribution policy
            distribution = DistributionPolicy.UNKNOWN
            fund_name = snapshot.get("Name", "") or getattr(fund, "name", "")
            if "acc" in fund_name.lower():
                distribution = DistributionPolicy.ACCUMULATING
            elif "dist" in fund_name.lower() or "div" in fund_name.lower():
                distribution = DistributionPolicy.DISTRIBUTING

            return SourceRecord(
                isin=snapshot.get("Isin", isin),
                name=fund_name or isin,
                source=self.name,
                instrument_type=instrument_type,
                currency=snapshot.get("Currency", {}).get("Id", "EUR") if isinstance(snapshot.get("Currency"), dict) else "EUR",
                domicile=snapshot.get("Domicile"),
                distribution=distribution,
                category_morningstar=category,
                ter=safe_float(snapshot.get("OngoingCharge")),
                performance=perf,
                risk=RiskMetrics(
                    sharpe_ratio_3y=safe_float(trailing.get("morningstarRatingFor3Year")),
                ),
                raw_data={
                    "snapshot": snapshot,
                    "trailing": trailing,
                },
            )

        except Exception as e:
            self.logger.error(f"Failed to get {isin} from Morningstar: {e}")
            return None

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
            import mstarpy.funds as ms_funds

            fund = ms_funds.Funds(isin)
            nav_data = fund.nav(start_date=start_date, end_date=end_date)

            if nav_data:
                return {
                    "dates": [d.get("date") for d in nav_data if d.get("date")],
                    "values": [d.get("nav") for d in nav_data if d.get("nav")],
                }

        except Exception as e:
            self.logger.error(f"Failed to get NAV history for {isin}: {e}")

        return None

    def health_check(self) -> bool:
        """Verifica se mstarpy è funzionante."""
        if not self._check_mstarpy():
            return False

        try:
            import mstarpy.funds as ms_funds
            # Prova a creare un oggetto Funds con ISIN noto
            fund = ms_funds.Funds("IE00B4L5Y983")
            return fund.name is not None
        except Exception as e:
            self.logger.error(f"Morningstar health check failed: {e}")
            return False
