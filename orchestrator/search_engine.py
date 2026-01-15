"""
Search Engine - Orchestratore principale per ricerche multi-fonte.

Coordina gli scraper, gestisce ricerche parallele e aggrega i risultati.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Callable, Dict
import logging

from scrapers.base import BaseDataSource
from scrapers.justetf_scraper import JustETFScraper
from scrapers.morningstar_scraper import MorningstarScraper
from scrapers.investiny_scraper import InvestinyScraper
from orchestrator.rate_limiter import get_rate_limiter
from aggregator.data_merger import DataMerger
from core.models import SearchCriteria, AggregatedInstrument, InstrumentType

logger = logging.getLogger(__name__)

# Type alias
ProgressCallback = Callable[[float, str], None]


class SearchEngine:
    """
    Orchestratore principale per ricerche multi-fonte.

    Responsabilità:
    - Coordinare ricerche parallele su più piattaforme
    - Gestire progress callbacks per l'UI
    - Aggregare e deduplicare i risultati via ISIN
    - Applicare filtri finali sui dati aggregati
    """

    def __init__(self, max_workers: int = 3):
        """
        Inizializza il search engine.

        Args:
            max_workers: Numero massimo di thread per ricerche parallele
        """
        self.rate_limiter = get_rate_limiter()
        self.max_workers = max_workers
        self.merger = DataMerger()

        # Inizializza scrapers
        self.scrapers: Dict[str, BaseDataSource] = {
            "justetf": JustETFScraper(),
            "morningstar": MorningstarScraper(),
            "investiny": InvestinyScraper(),
        }

        # Priorità fonti (ordine di preferenza per dati)
        self.source_priority = ["morningstar", "justetf", "investiny"]

    def search(
        self,
        criteria: SearchCriteria,
        progress_callback: Optional[ProgressCallback] = None,
        sources: Optional[List[str]] = None
    ) -> List[AggregatedInstrument]:
        """
        Esegue ricerca su tutte le fonti e aggrega i risultati.

        Args:
            criteria: Criteri di ricerca
            progress_callback: Callback per progress bar (0.0-1.0, messaggio)
            sources: Lista fonti da usare (default: tutte)

        Returns:
            Lista di strumenti aggregati e deduplicati
        """
        if sources is None:
            sources = list(self.scrapers.keys())

        # Filtra fonti in base ai tipi strumento richiesti
        active_sources = self._filter_sources_by_type(sources, criteria.instrument_types)

        if not active_sources:
            logger.warning("No active sources for the requested instrument types")
            return []

        self._update_progress(progress_callback, 0.0, "Avvio ricerca multi-fonte...")

        all_records = []
        source_results: Dict[str, List] = {}

        # Esegui ricerche in parallelo
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {}

            for source_name in active_sources:
                scraper = self.scrapers[source_name]

                # Crea callback parziale per questa fonte
                def make_callback(src_name: str, total_sources: int):
                    def cb(progress: float, message: str):
                        if progress_callback:
                            # Scala progress per questa fonte
                            base = active_sources.index(src_name) / total_sources
                            scaled = base + (progress / total_sources)
                            progress_callback(scaled * 0.7, f"[{src_name}] {message}")
                    return cb

                cb = make_callback(source_name, len(active_sources))
                future = executor.submit(scraper.search, criteria, cb)
                futures[future] = source_name

            # Raccogli risultati
            for future in as_completed(futures):
                source_name = futures[future]
                try:
                    records = future.result(timeout=120)  # 2 min timeout
                    source_results[source_name] = records
                    all_records.extend(records)
                    logger.info(f"{source_name}: found {len(records)} records")
                except Exception as e:
                    logger.error(f"{source_name} failed: {e}")
                    source_results[source_name] = []

        self._update_progress(progress_callback, 0.7, "Aggregazione risultati...")

        # Aggrega e deduplica via ISIN
        aggregated = self.merger.merge(all_records, self.source_priority)

        self._update_progress(progress_callback, 0.9, "Applicazione filtri finali...")

        # Applica filtro performance minima sui dati aggregati
        if criteria.min_performance is not None:
            aggregated = self._filter_by_performance(
                aggregated,
                criteria.min_performance,
                criteria.performance_period
            )

        self._update_progress(
            progress_callback,
            1.0,
            f"Completato: {len(aggregated)} strumenti trovati"
        )

        return aggregated

    def _filter_sources_by_type(
        self,
        sources: List[str],
        types: List[InstrumentType]
    ) -> List[str]:
        """
        Filtra le fonti che supportano i tipi strumento richiesti.

        Args:
            sources: Lista nomi fonti
            types: Tipi strumento richiesti

        Returns:
            Lista fonti che supportano almeno uno dei tipi
        """
        result = []
        for source_name in sources:
            scraper = self.scrapers.get(source_name)
            if scraper:
                supported = scraper.supported_types
                if any(t in supported for t in types):
                    result.append(source_name)
        return result

    def _filter_by_performance(
        self,
        instruments: List[AggregatedInstrument],
        min_perf: float,
        period: str
    ) -> List[AggregatedInstrument]:
        """
        Filtra strumenti per performance minima.

        Args:
            instruments: Lista strumenti aggregati
            min_perf: Performance minima richiesta
            period: Periodo di riferimento (ytd, 1y, 3y, 5y, 10y)

        Returns:
            Lista filtrata
        """
        attr_map = {
            "ytd": "perf_ytd_eur",
            "1y": "perf_1y_eur",
            "3y": "perf_3y_eur",
            "5y": "perf_5y_eur",
            "7y": "perf_7y_eur",
            "10y": "perf_10y_eur",
        }
        attr = attr_map.get(period, "perf_3y_eur")

        return [
            inst for inst in instruments
            if getattr(inst, attr, None) is not None
            and getattr(inst, attr) >= min_perf
        ]

    def enrich_by_isins(
        self,
        isins: List[str],
        progress_callback: Optional[ProgressCallback] = None
    ) -> List[AggregatedInstrument]:
        """
        Arricchisce una lista di ISIN con dati da tutte le fonti.

        Utile per lookup specifici quando si ha già una lista di ISIN.

        Args:
            isins: Lista di codici ISIN
            progress_callback: Callback per progress

        Returns:
            Lista di strumenti aggregati
        """
        all_records = []
        total = len(isins) * len(self.scrapers)
        current = 0

        for isin in isins:
            for source_name, scraper in self.scrapers.items():
                try:
                    self.rate_limiter.wait(source_name)
                    record = scraper.get_by_isin(isin)
                    if record:
                        all_records.append(record)
                except Exception as e:
                    logger.warning(f"Failed to get {isin} from {source_name}: {e}")

                current += 1
                self._update_progress(
                    progress_callback,
                    current / total,
                    f"Lookup {isin}..."
                )

        return self.merger.merge(all_records, self.source_priority)

    def health_check(self) -> Dict[str, bool]:
        """
        Verifica stato di tutti gli scraper.

        Returns:
            Dict con stato (True/False) per ogni fonte
        """
        status = {}
        for name, scraper in self.scrapers.items():
            try:
                status[name] = scraper.health_check()
            except Exception:
                status[name] = False
        return status

    def get_available_sources(self) -> List[str]:
        """
        Restituisce lista delle fonti disponibili.

        Returns:
            Lista nomi fonti configurate
        """
        return list(self.scrapers.keys())

    def _update_progress(
        self,
        callback: Optional[ProgressCallback],
        progress: float,
        message: str
    ) -> None:
        """Helper per aggiornare progress callback in modo sicuro."""
        if callback:
            try:
                callback(min(1.0, max(0.0, progress)), message)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
