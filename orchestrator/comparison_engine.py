"""
Comparison Engine - Motore di confronto fondi universo vs ETF.

Implementa la logica di confronto tra i fondi dell'universo utente
e gli ETF di mercato, calcolando delta di performance e statistiche.
"""
import logging
from typing import List, Optional, Dict, Callable
from datetime import datetime

from core.models import (
    UniverseInstrument,
    AggregatedInstrument,
    ComparisonResult,
    ComparisonReport,
    SearchCriteria,
    InstrumentType,
)
from orchestrator.search_engine import SearchEngine
from aggregator.data_merger import DataMerger
from config import CATEGORY_MAPPING

logger = logging.getLogger(__name__)

# Type alias
ProgressCallback = Callable[[float, str], None]


class ComparisonEngine:
    """
    Motore di confronto fondi universo vs ETF.

    Supporta due modalità operative:
    1. Universo vs ETF per categoria: confronta fondi dell'universo con ETF della stessa categoria
    2. ETF vs Universo: confronta un ETF specifico con i fondi dell'universo
    """

    # Periodi disponibili per il confronto
    ALL_PERIODS = ["1m", "3m", "6m", "ytd", "1y", "3y", "5y", "7y", "9y", "10y"]

    def __init__(self, search_engine: Optional[SearchEngine] = None):
        """
        Inizializza il comparison engine.

        Args:
            search_engine: SearchEngine per recupero dati. Se None, crea nuova istanza.
        """
        self.search_engine = search_engine or SearchEngine()
        self.merger = DataMerger()

    def compare_universe_vs_etf_by_category(
        self,
        universe: List[UniverseInstrument],
        category: str,
        category_type: str = "morningstar",
        periods: Optional[List[str]] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ComparisonReport:
        """
        Confronta fondi universo con ETF della stessa categoria.

        Args:
            universe: Lista strumenti universo utente
            category: Categoria per il confronto
            category_type: "morningstar" o "assogestioni"
            periods: Lista periodi da analizzare (default: tutti)
            progress_callback: Callback per progress bar

        Returns:
            ComparisonReport con risultati e statistiche
        """
        periods = periods or self.ALL_PERIODS

        report = ComparisonReport(
            comparison_type="universe_vs_etf",
            category=category,
            category_type=category_type,
            periods_analyzed=periods,
            generated_at=datetime.now()
        )

        self._update_progress(progress_callback, 0.0, "Avvio confronto...")

        # Step 1: Filtra universo per categoria
        self._update_progress(progress_callback, 0.1, "Filtraggio universo per categoria...")

        filtered_universe = self._filter_universe_by_category(
            universe, category, category_type
        )

        if not filtered_universe:
            logger.warning(f"Nessun fondo nell'universo per categoria: {category}")
            # Cerca comunque ETF per mostrare il mercato
            filtered_universe = universe  # Usa tutto l'universo se nessun match

        # Step 2: Arricchisci fondi universo con dati dalle fonti
        self._update_progress(progress_callback, 0.2, "Recupero dati fondi universo...")

        universe_isins = [inst.isin for inst in filtered_universe]
        enriched_universe = self.search_engine.enrich_by_isins(
            universe_isins,
            progress_callback=lambda p, m: self._update_progress(
                progress_callback, 0.2 + p * 0.3, f"[Universo] {m}"
            )
        )

        # Step 3: Cerca ETF della stessa categoria
        self._update_progress(progress_callback, 0.5, "Ricerca ETF di mercato...")

        # Mappa categoria se necessario (Assogestioni -> Morningstar)
        search_categories = self._map_category(category, category_type)

        criteria = SearchCriteria(
            categories_morningstar=search_categories if category_type == "morningstar" else [],
            categories_assogestioni=[category] if category_type == "assogestioni" else [],
            instrument_types=[InstrumentType.ETF],
        )

        market_etfs = self.search_engine.search(
            criteria,
            progress_callback=lambda p, m: self._update_progress(
                progress_callback, 0.5 + p * 0.2, f"[Mercato] {m}"
            )
        )

        # Step 4: Seleziona ETF benchmark (quello con più dati o primo disponibile)
        self._update_progress(progress_callback, 0.7, "Selezione benchmark ETF...")

        benchmark_etf = self._select_benchmark_etf(market_etfs)
        report.benchmark_etf = benchmark_etf

        # Step 5: Calcola delta e crea risultati
        self._update_progress(progress_callback, 0.8, "Calcolo delta performance...")

        # Aggiungi fondi universo ai risultati
        for inst in enriched_universe:
            deltas = self._calculate_deltas(inst, benchmark_etf, periods) if benchmark_etf else {}
            result = ComparisonResult(
                instrument=inst,
                origin="universe",
                benchmark_isin=benchmark_etf.isin if benchmark_etf else None,
                delta_1m=deltas.get("1m"),
                delta_3m=deltas.get("3m"),
                delta_6m=deltas.get("6m"),
                delta_ytd=deltas.get("ytd"),
                delta_1y=deltas.get("1y"),
                delta_3y=deltas.get("3y"),
                delta_5y=deltas.get("5y"),
                delta_7y=deltas.get("7y"),
                delta_9y=deltas.get("9y"),
                delta_10y=deltas.get("10y"),
            )
            report.results.append(result)

        # Aggiungi ETF benchmark ai risultati (senza delta)
        if benchmark_etf:
            result = ComparisonResult(
                instrument=benchmark_etf,
                origin="market",
                benchmark_isin=None,
            )
            report.results.append(result)

        # Step 6: Calcola statistiche
        self._update_progress(progress_callback, 0.9, "Calcolo statistiche...")

        report.calculate_statistics(reference_period="3y")

        self._update_progress(
            progress_callback,
            1.0,
            f"Confronto completato: {len(report.results)} strumenti"
        )

        return report

    def compare_etf_vs_universe(
        self,
        etf_isin: str,
        universe: List[UniverseInstrument],
        filter_by_category: bool = True,
        periods: Optional[List[str]] = None,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ComparisonReport:
        """
        Confronta un ETF specifico con i fondi dell'universo.

        Args:
            etf_isin: ISIN dell'ETF da confrontare
            universe: Lista strumenti universo utente
            filter_by_category: Se True, mostra solo fondi della stessa categoria
            periods: Lista periodi da analizzare
            progress_callback: Callback per progress bar

        Returns:
            ComparisonReport con risultati e statistiche
        """
        periods = periods or self.ALL_PERIODS

        report = ComparisonReport(
            comparison_type="etf_vs_universe",
            periods_analyzed=periods,
            generated_at=datetime.now()
        )

        self._update_progress(progress_callback, 0.0, "Avvio confronto ETF vs Universo...")

        # Step 1: Recupera dati ETF
        self._update_progress(progress_callback, 0.1, "Recupero dati ETF...")

        etf_results = self.search_engine.enrich_by_isins([etf_isin])
        if not etf_results:
            logger.error(f"ETF {etf_isin} non trovato")
            return report

        benchmark_etf = etf_results[0]
        report.benchmark_etf = benchmark_etf
        report.category = benchmark_etf.category_morningstar or benchmark_etf.category_assogestioni

        # Determina tipo categoria
        if benchmark_etf.category_morningstar:
            report.category_type = "morningstar"
        elif benchmark_etf.category_assogestioni:
            report.category_type = "assogestioni"

        # Step 2: Filtra universo per categoria se richiesto
        self._update_progress(progress_callback, 0.3, "Filtraggio universo...")

        if filter_by_category and report.category:
            filtered_universe = self._filter_universe_by_category(
                universe,
                report.category,
                report.category_type or "morningstar"
            )
        else:
            filtered_universe = universe

        if not filtered_universe:
            logger.warning("Nessun fondo nell'universo corrisponde alla categoria ETF")
            filtered_universe = universe  # Mostra tutto se nessun match

        # Step 3: Arricchisci fondi universo
        self._update_progress(progress_callback, 0.4, "Recupero dati fondi universo...")

        universe_isins = [inst.isin for inst in filtered_universe]
        enriched_universe = self.search_engine.enrich_by_isins(
            universe_isins,
            progress_callback=lambda p, m: self._update_progress(
                progress_callback, 0.4 + p * 0.4, f"[Universo] {m}"
            )
        )

        # Step 4: Calcola delta e crea risultati
        self._update_progress(progress_callback, 0.8, "Calcolo delta performance...")

        # Aggiungi ETF benchmark ai risultati (primo)
        result = ComparisonResult(
            instrument=benchmark_etf,
            origin="market",
            benchmark_isin=None,
        )
        report.results.append(result)

        # Aggiungi fondi universo
        for inst in enriched_universe:
            deltas = self._calculate_deltas(inst, benchmark_etf, periods)
            result = ComparisonResult(
                instrument=inst,
                origin="universe",
                benchmark_isin=benchmark_etf.isin,
                delta_1m=deltas.get("1m"),
                delta_3m=deltas.get("3m"),
                delta_6m=deltas.get("6m"),
                delta_ytd=deltas.get("ytd"),
                delta_1y=deltas.get("1y"),
                delta_3y=deltas.get("3y"),
                delta_5y=deltas.get("5y"),
                delta_7y=deltas.get("7y"),
                delta_9y=deltas.get("9y"),
                delta_10y=deltas.get("10y"),
            )
            report.results.append(result)

        # Step 5: Calcola statistiche
        self._update_progress(progress_callback, 0.9, "Calcolo statistiche...")

        report.calculate_statistics(reference_period="3y")

        self._update_progress(
            progress_callback,
            1.0,
            f"Confronto completato: {len(report.results)} strumenti"
        )

        return report

    def search_etf_by_name(
        self,
        query: str,
        max_results: int = 10
    ) -> List[AggregatedInstrument]:
        """
        Cerca ETF per nome o parte del nome.

        Args:
            query: Stringa di ricerca
            max_results: Numero massimo risultati

        Returns:
            Lista ETF corrispondenti
        """
        # Cerca con criteri minimali
        criteria = SearchCriteria(
            instrument_types=[InstrumentType.ETF],
        )

        all_etfs = self.search_engine.search(criteria)

        # Filtra per nome
        query_lower = query.lower()
        matching = [
            etf for etf in all_etfs
            if query_lower in etf.name.lower() or query_lower in etf.isin.lower()
        ]

        return matching[:max_results]

    def _filter_universe_by_category(
        self,
        universe: List[UniverseInstrument],
        category: str,
        category_type: str
    ) -> List[UniverseInstrument]:
        """
        Filtra l'universo per categoria.

        Args:
            universe: Lista strumenti universo
            category: Categoria target
            category_type: Tipo sistema categorizzazione

        Returns:
            Lista strumenti filtrati
        """
        # Match esatto sulla categoria dell'universo
        filtered = []
        category_lower = category.lower()

        for inst in universe:
            if inst.category:
                if inst.category.lower() == category_lower:
                    filtered.append(inst)
                # Prova match parziale
                elif category_lower in inst.category.lower():
                    filtered.append(inst)
                elif inst.category.lower() in category_lower:
                    filtered.append(inst)

        # Se nessun match, prova con mapping categorie
        if not filtered and category_type == "morningstar":
            # Cerca nel mapping inverso (Morningstar -> Assogestioni)
            for asso_cat, ms_cats in CATEGORY_MAPPING.items():
                if category in ms_cats:
                    for inst in universe:
                        if inst.category and asso_cat.lower() in inst.category.lower():
                            filtered.append(inst)

        return filtered

    def _map_category(
        self,
        category: str,
        category_type: str
    ) -> List[str]:
        """
        Mappa categoria tra sistemi (Assogestioni -> Morningstar).

        Args:
            category: Categoria da mappare
            category_type: Tipo categoria originale

        Returns:
            Lista categorie mappate (per ricerca)
        """
        if category_type == "morningstar":
            return [category]

        # Mappa Assogestioni -> Morningstar
        if category in CATEGORY_MAPPING:
            return CATEGORY_MAPPING[category]

        # Prova match parziale
        category_upper = category.upper()
        for asso_cat, ms_cats in CATEGORY_MAPPING.items():
            if asso_cat in category_upper or category_upper in asso_cat:
                return ms_cats

        # Fallback: usa categoria originale
        return [category]

    def _select_benchmark_etf(
        self,
        etfs: List[AggregatedInstrument]
    ) -> Optional[AggregatedInstrument]:
        """
        Seleziona l'ETF benchmark dal gruppo.

        Criteri di selezione (in ordine):
        1. ETF con più dati di performance disponibili
        2. ETF con quality score più alto
        3. Primo ETF nella lista

        Args:
            etfs: Lista ETF candidati

        Returns:
            ETF selezionato o None
        """
        if not etfs:
            return None

        # Calcola score per ogni ETF
        def calculate_score(etf: AggregatedInstrument) -> float:
            score = 0.0

            # Punti per dati performance disponibili
            if etf.perf_1m_eur is not None:
                score += 1
            if etf.perf_3m_eur is not None:
                score += 1
            if etf.perf_6m_eur is not None:
                score += 1
            if etf.perf_ytd_eur is not None:
                score += 2
            if etf.perf_1y_eur is not None:
                score += 3
            if etf.perf_3y_eur is not None:
                score += 5
            if etf.perf_5y_eur is not None:
                score += 5
            if etf.perf_7y_eur is not None:
                score += 3
            if etf.perf_9y_eur is not None:
                score += 2
            if etf.perf_10y_eur is not None:
                score += 3

            # Bonus per quality score
            score += etf.data_quality_score / 10

            return score

        # Ordina per score e restituisci il migliore
        sorted_etfs = sorted(etfs, key=calculate_score, reverse=True)
        return sorted_etfs[0]

    def _calculate_deltas(
        self,
        instrument: AggregatedInstrument,
        benchmark: Optional[AggregatedInstrument],
        periods: List[str]
    ) -> Dict[str, Optional[float]]:
        """
        Calcola differenze di performance tra strumento e benchmark.

        Args:
            instrument: Strumento da confrontare
            benchmark: ETF benchmark
            periods: Lista periodi da calcolare

        Returns:
            Dict periodo -> delta (strumento - benchmark)
        """
        deltas: Dict[str, Optional[float]] = {}

        if not benchmark:
            return deltas

        for period in periods:
            inst_perf = instrument.get_performance_by_period(period)
            bench_perf = benchmark.get_performance_by_period(period)

            if inst_perf is not None and bench_perf is not None:
                deltas[period] = round(inst_perf - bench_perf, 2)
            else:
                deltas[period] = None

        return deltas

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
