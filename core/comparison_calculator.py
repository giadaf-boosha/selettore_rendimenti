"""
Comparison Calculator - Calcola delta performance vs ETF benchmark.

Questo modulo implementa la logica di confronto tra i fondi dell'universo
utente e un ETF benchmark, calcolando il delta di performance e
classificando i fondi in base a chi batte o meno l'ETF.
"""
from typing import List, Optional
from dataclasses import dataclass, field
from core.models import UniverseInstrument
import logging

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Risultato confronto singolo fondo vs ETF."""
    instrument: UniverseInstrument
    etf_performance: Optional[float]
    fund_performance: Optional[float]
    delta: Optional[float]
    beats_etf: Optional[bool]  # True = batte, False = non batte, None = N/A

    @property
    def status(self) -> str:
        """Restituisce lo status testuale del confronto."""
        if self.beats_etf is True:
            return "BATTE"
        elif self.beats_etf is False:
            return "NON BATTE"
        else:
            return "N/A"

    @property
    def status_emoji(self) -> str:
        """Restituisce lo status con emoji."""
        if self.beats_etf is True:
            return "✅ BATTE"
        elif self.beats_etf is False:
            return "❌ NON BATTE"
        else:
            return "⚪ N/A"


@dataclass
class ComparisonReport:
    """Report completo confronto universo vs ETF."""
    etf_benchmark: UniverseInstrument
    period: str
    period_label: str
    results: List[ComparisonResult] = field(default_factory=list)

    @property
    def total_funds(self) -> int:
        """Numero totale di fondi confrontati."""
        return len(self.results)

    @property
    def funds_beating_etf(self) -> int:
        """Numero di fondi che battono l'ETF."""
        return sum(1 for r in self.results if r.beats_etf is True)

    @property
    def funds_not_beating_etf(self) -> int:
        """Numero di fondi che non battono l'ETF."""
        return sum(1 for r in self.results if r.beats_etf is False)

    @property
    def funds_no_data(self) -> int:
        """Numero di fondi senza dati per il confronto."""
        return sum(1 for r in self.results if r.beats_etf is None)

    @property
    def etf_performance(self) -> Optional[float]:
        """Performance dell'ETF nel periodo selezionato."""
        return self.etf_benchmark.get_performance_by_period(self.period)

    @property
    def avg_delta(self) -> Optional[float]:
        """Media dei delta (solo per fondi con dati)."""
        deltas = [r.delta for r in self.results if r.delta is not None]
        if deltas:
            return sum(deltas) / len(deltas)
        return None

    @property
    def best_performer(self) -> Optional[ComparisonResult]:
        """Fondo con il miglior delta."""
        valid = [r for r in self.results if r.delta is not None]
        if valid:
            return max(valid, key=lambda r: r.delta if r.delta is not None else float('-inf'))
        return None

    @property
    def worst_performer(self) -> Optional[ComparisonResult]:
        """Fondo con il peggior delta."""
        valid = [r for r in self.results if r.delta is not None]
        if valid:
            return min(valid, key=lambda r: r.delta if r.delta is not None else float('inf'))
        return None

    @property
    def beat_percentage(self) -> float:
        """Percentuale di fondi che battono l'ETF (su quelli con dati)."""
        with_data = self.funds_beating_etf + self.funds_not_beating_etf
        if with_data > 0:
            return (self.funds_beating_etf / with_data) * 100
        return 0.0

    def get_sorted_results(self, ascending: bool = False) -> List[ComparisonResult]:
        """
        Restituisce risultati ordinati per delta (default: migliori prima).

        Args:
            ascending: Se True, ordina dal peggiore al migliore

        Returns:
            Lista di risultati ordinata
        """
        # Separa risultati con e senza delta
        with_delta = [r for r in self.results if r.delta is not None]
        without_delta = [r for r in self.results if r.delta is None]

        # Ordina quelli con delta
        sorted_with_delta = sorted(
            with_delta,
            key=lambda r: r.delta if r.delta is not None else 0.0,
            reverse=not ascending
        )

        # Risultati senza delta alla fine
        return sorted_with_delta + without_delta


def compare_universe_vs_etf(
    universe: List[UniverseInstrument],
    etf_benchmark: UniverseInstrument,
    period: str,
    period_label: str
) -> ComparisonReport:
    """
    Confronta tutti i fondi dell'universo con l'ETF benchmark.

    Args:
        universe: Lista fondi da confrontare
        etf_benchmark: ETF di riferimento
        period: Codice periodo (1m, 3m, 6m, ytd, 1y, 3y, 5y, 7y, 9y, 10y)
        period_label: Label periodo per display (es. "3 anni")

    Returns:
        ComparisonReport con tutti i risultati
    """
    report = ComparisonReport(
        etf_benchmark=etf_benchmark,
        period=period,
        period_label=period_label
    )

    etf_perf = etf_benchmark.get_performance_by_period(period)

    for fund in universe:
        # Escludi l'ETF stesso dal confronto
        if fund.isin == etf_benchmark.isin:
            continue

        fund_perf = fund.get_performance_by_period(period)

        # Calcola delta e status
        if etf_perf is not None and fund_perf is not None:
            delta = round(fund_perf - etf_perf, 4)  # In decimale
            beats_etf = delta > 0
        else:
            delta = None
            beats_etf = None

        result = ComparisonResult(
            instrument=fund,
            etf_performance=etf_perf,
            fund_performance=fund_perf,
            delta=delta,
            beats_etf=beats_etf
        )

        report.results.append(result)

    logger.info(
        f"Confronto completato: {report.funds_beating_etf} battono ETF, "
        f"{report.funds_not_beating_etf} non battono, {report.funds_no_data} N/A"
    )

    return report
