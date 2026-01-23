"""
Scraper per JustETF.com

Fonte primaria per ETF europei. Utilizza la libreria justetf-scraping
per recuperare dati su oltre 3400 ETF.
"""
import pandas as pd
from typing import List, Optional
from time import time
from datetime import datetime
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


class JustETFScraper(BaseDataSource):
    """
    Scraper per JustETF.com

    Fonte primaria per ETF europei. Fornisce dati completi su:
    - Performance (YTD, 1a, 3a, 5a, 10a)
    - Volatilità e Sharpe ratio
    - TER (Total Expense Ratio)
    - Politica distribuzione
    """

    def __init__(self):
        # Rate limit increased to 2.0s to avoid triggering anti-bot measures
        super().__init__(name="justetf", rate_limit=2.0)
        self._overview_cache: Optional[pd.DataFrame] = None
        self._cache_timestamp: Optional[float] = None
        self._cache_ttl: int = 3600  # 1 ora

    @property
    def supported_types(self) -> List[InstrumentType]:
        return [InstrumentType.ETF]

    def _get_overview(self, force_refresh: bool = False) -> pd.DataFrame:
        """
        Carica overview ETF con caching.

        La funzione load_overview() di justetf-scraping è lenta
        (fa multiple richieste), quindi implementiamo cache locale.
        """
        now = time()

        # Verifica cache
        if (
            not force_refresh
            and self._overview_cache is not None
            and self._cache_timestamp
            and (now - self._cache_timestamp) < self._cache_ttl
        ):
            self.logger.debug("Using cached JustETF overview")
            return self._overview_cache

        self.logger.info("Loading JustETF overview (this may take a while)...")

        try:
            import justetf_scraping

            # Carica overview con dati arricchiti
            df = justetf_scraping.load_overview(enrich=True)

            self._overview_cache = df
            self._cache_timestamp = now

            self.logger.info(f"Loaded {len(df)} ETFs from JustETF")
            return df

        except ImportError:
            self.logger.error("justetf-scraping not installed. Run: pip install justetf-scraping")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load JustETF overview: {e}")
            raise

    def _map_distribution(self, use_of_profits: str) -> DistributionPolicy:
        """Mappa il campo use_of_profits di JustETF."""
        if pd.isna(use_of_profits) or not use_of_profits:
            return DistributionPolicy.UNKNOWN

        val = str(use_of_profits).lower()
        if "accumulat" in val:
            return DistributionPolicy.ACCUMULATING
        elif "distribut" in val:
            return DistributionPolicy.DISTRIBUTING
        return DistributionPolicy.UNKNOWN

    def _normalize_performance(self, value) -> Optional[float]:
        """
        Normalizza il valore di performance da percentuale a decimale.

        JustETF restituisce le performance in formato percentuale (es. 5.93 = 5.93%).
        Il sistema interno usa formato decimale (es. 0.0593 = 5.93%).
        Questa funzione divide per 100 per convertire.
        """
        val = safe_float(value)
        if val is not None:
            return val / 100.0
        return None

    def _row_to_record(self, row: pd.Series) -> SourceRecord:
        """Converte una riga DataFrame in SourceRecord."""
        inception = None
        if pd.notna(row.get("inception_date")):
            try:
                inception = pd.to_datetime(row["inception_date"])
            except Exception:
                pass

        # ISIN è l'indice del DataFrame, non una colonna
        isin = str(row.name) if hasattr(row, 'name') else ""

        return SourceRecord(
            isin=isin,
            name=str(row.get("name", "")),
            source=self.name,
            instrument_type=InstrumentType.ETF,
            currency=str(row.get("currency", "EUR")),
            domicile=str(row.get("domicile_country", "")) if pd.notna(row.get("domicile_country")) else None,
            distribution=self._map_distribution(row.get("dividends")),  # "dividends" non "use_of_profits"
            category_morningstar=None,  # JustETF non fornisce categorie Morningstar
            category_assogestioni=None,
            ter=safe_float(row.get("ter")),
            aum=safe_float(row.get("size")),  # "size" non "fund_size"
            inception_date=inception,
            performance=PerformanceData(
                # Normalizza performance da % a decimale (JustETF restituisce %)
                ytd=self._normalize_performance(row.get("last_six_months")),
                return_1y=self._normalize_performance(row.get("last_year")),
                return_3y=self._normalize_performance(row.get("last_three_years")),
                return_5y=self._normalize_performance(row.get("last_five_years")),
                return_10y=None,  # JustETF non fornisce 10y direttamente
            ),
            risk=RiskMetrics(
                volatility_1y=safe_float(row.get("last_year_volatility")),
                volatility_3y=safe_float(row.get("last_three_years_volatility")),
                volatility_5y=safe_float(row.get("last_five_years_volatility")),
                sharpe_ratio_3y=safe_float(row.get("last_three_years_return_per_risk")),
                max_drawdown=safe_float(row.get("max_drawdown")),
            ),
            raw_data=row.to_dict() if hasattr(row, 'to_dict') else {},
        )

    def _get_perf_column(self, period: str) -> str:
        """Mappa periodo al nome colonna JustETF."""
        mapping = {
            "ytd": "last_six_months",  # YTD approssimato
            "1y": "last_year",
            "3y": "last_three_years",
            "5y": "last_five_years",
            "10y": "last_five_years",  # Fallback a 5y
        }
        return mapping.get(period, "last_three_years")

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def search(
        self,
        criteria: SearchCriteria,
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[SourceRecord]:
        """
        Cerca ETF secondo i criteri specificati.

        JustETF non supporta filtri per categoria Assogestioni/Morningstar,
        quindi filtriamo solo per valuta e distribuzione.
        """
        self._update_progress(progress_callback, 0.1, "Caricamento dati JustETF...")

        try:
            df = self._get_overview()
        except Exception as e:
            self.logger.error(f"Failed to get JustETF data: {e}")
            self._update_progress(progress_callback, 1.0, f"Errore JustETF: {e}")
            return []

        self._update_progress(progress_callback, 0.5, "Applicazione filtri JustETF...")

        # Inizia con tutti i record
        mask = pd.Series([True] * len(df), index=df.index)

        # Filtro valuta
        if criteria.currencies:
            if "currency" in df.columns:
                mask &= df["currency"].isin(criteria.currencies)

        # Filtro distribuzione
        if criteria.distribution_filter:
            if "dividends" in df.columns:
                if criteria.distribution_filter == DistributionPolicy.ACCUMULATING:
                    mask &= df["dividends"].str.lower().str.contains("accumulat", na=False)
                elif criteria.distribution_filter == DistributionPolicy.DISTRIBUTING:
                    mask &= df["dividends"].str.lower().str.contains("distribut", na=False)

        # Filtro performance minima (applicato qui per efficienza)
        if criteria.min_performance is not None:
            perf_col = self._get_perf_column(criteria.performance_period)
            if perf_col in df.columns:
                # Considera solo record con performance non-null
                has_perf = df[perf_col].notna()
                meets_threshold = df[perf_col] >= criteria.min_performance
                mask &= (has_perf & meets_threshold)

        filtered_df = df[mask]

        self._update_progress(
            progress_callback,
            0.8,
            f"Trovati {len(filtered_df)} ETF su JustETF"
        )

        # Converti in SourceRecord
        records = []
        for _, row in filtered_df.iterrows():
            try:
                record = self._row_to_record(row)
                if record.isin:  # Ignora record senza ISIN
                    records.append(record)
            except Exception as e:
                self.logger.warning(f"Failed to parse row: {e}")

        self._update_progress(progress_callback, 1.0, f"JustETF: {len(records)} ETF")

        return records

    @retry_with_backoff(max_retries=3, base_delay=2.0)
    def get_by_isin(self, isin: str) -> Optional[SourceRecord]:
        """Recupera singolo ETF per ISIN."""
        try:
            df = self._get_overview()
            isin_upper = isin.upper()

            # ISIN è l'indice del DataFrame
            if isin_upper in df.index:
                return self._row_to_record(df.loc[isin_upper])
            else:
                self.logger.debug(f"ISIN {isin} not found in JustETF")
                return None

        except Exception as e:
            self.logger.error(f"Failed to get ISIN {isin}: {e}")
            return None

    def get_performance_history(
        self,
        isin: str,
        start_date: str,
        end_date: str
    ) -> Optional[dict]:
        """Recupera storico quotazioni con load_chart()."""
        self._wait_rate_limit()

        try:
            import justetf_scraping

            df = justetf_scraping.load_chart(isin)

            # Filtra per date
            df.index = pd.to_datetime(df.index)
            mask = (df.index >= start_date) & (df.index <= end_date)
            filtered = df[mask]

            if filtered.empty:
                return None

            return {
                "dates": filtered.index.strftime("%Y-%m-%d").tolist(),
                "values": filtered["quote_with_dividends"].tolist()
                if "quote_with_dividends" in filtered.columns
                else filtered.iloc[:, 0].tolist(),
            }

        except Exception as e:
            self.logger.error(f"Failed to get chart for {isin}: {e}")
            return None

    def health_check(self) -> bool:
        """Verifica se JustETF è raggiungibile."""
        try:
            import justetf_scraping
            # Prova a caricare overview (usa cache se disponibile)
            df = self._get_overview()
            return len(df) > 0
        except Exception as e:
            self.logger.error(f"JustETF health check failed: {e}")
            return False
