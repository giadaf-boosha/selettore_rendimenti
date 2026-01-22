"""
Modelli dati per Selettore Rendimenti Fondi/ETF.

Questo modulo definisce tutti i dataclass utilizzati nel sistema:
- SourceRecord: record grezzo da singola fonte
- AggregatedInstrument: record aggregato da multiple fonti
- SearchCriteria: criteri di ricerca dall'interfaccia utente
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum
import re


class InstrumentType(Enum):
    """Tipo di strumento finanziario."""
    ETF = "ETF"
    FUND = "FUND"
    UNKNOWN = "UNKNOWN"


class DistributionPolicy(Enum):
    """Politica di distribuzione dividendi/cedole."""
    ACCUMULATING = "ACC"
    DISTRIBUTING = "DIST"
    UNKNOWN = "UNKNOWN"


@dataclass
class PerformanceData:
    """Performance su diversi orizzonti temporali (in percentuale)."""
    return_1m: Optional[float] = None   # v3.0: 1 mese
    return_3m: Optional[float] = None   # v3.0: 3 mesi
    return_6m: Optional[float] = None   # v3.0: 6 mesi
    ytd: Optional[float] = None
    return_1y: Optional[float] = None
    return_3y: Optional[float] = None
    return_5y: Optional[float] = None
    return_7y: Optional[float] = None
    return_9y: Optional[float] = None   # v3.0: 9 anni
    return_10y: Optional[float] = None

    def get_by_period(self, period: str) -> Optional[float]:
        """Restituisce la performance per il periodo specificato."""
        mapping = {
            "1m": self.return_1m,
            "3m": self.return_3m,
            "6m": self.return_6m,
            "ytd": self.ytd,
            "1y": self.return_1y,
            "3y": self.return_3y,
            "5y": self.return_5y,
            "7y": self.return_7y,
            "9y": self.return_9y,
            "10y": self.return_10y,
        }
        return mapping.get(period)


@dataclass
class RiskMetrics:
    """Metriche di rischio."""
    volatility_1y: Optional[float] = None
    volatility_3y: Optional[float] = None
    volatility_5y: Optional[float] = None
    sharpe_ratio_3y: Optional[float] = None
    max_drawdown: Optional[float] = None


@dataclass
class SourceRecord:
    """
    Record grezzo proveniente da una singola fonte.

    Rappresenta i dati come forniti dalla piattaforma originale,
    prima dell'aggregazione.
    """
    isin: str
    name: str
    source: str  # "justetf", "morningstar", "investiny"
    instrument_type: InstrumentType = InstrumentType.UNKNOWN
    currency: str = "EUR"
    domicile: Optional[str] = None
    distribution: DistributionPolicy = DistributionPolicy.UNKNOWN
    category_morningstar: Optional[str] = None
    category_assogestioni: Optional[str] = None
    ter: Optional[float] = None  # Total Expense Ratio
    aum: Optional[float] = None  # Assets Under Management
    inception_date: Optional[datetime] = None
    performance: PerformanceData = field(default_factory=PerformanceData)
    risk: RiskMetrics = field(default_factory=RiskMetrics)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    retrieved_at: datetime = field(default_factory=datetime.now)

    def validate_isin(self) -> bool:
        """
        Valida il formato ISIN.

        Formato: 2 lettere paese + 9 alfanumerici + 1 check digit numerico
        Esempio: IE00B4L5Y983
        """
        if not self.isin or len(self.isin) != 12:
            return False
        pattern = r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$'
        return bool(re.match(pattern, self.isin))


@dataclass
class AggregatedInstrument:
    """
    Record aggregato da multiple fonti.

    Rappresenta i dati consolidati dopo il merge via ISIN,
    pronti per l'export in Excel.
    """
    isin: str
    name: str
    instrument_type: InstrumentType = InstrumentType.UNKNOWN
    currency: str = "EUR"
    domicile: Optional[str] = None
    distribution: DistributionPolicy = DistributionPolicy.UNKNOWN
    category_morningstar: Optional[str] = None
    category_assogestioni: Optional[str] = None

    # Performance in EUR (estese v3.0)
    perf_1m_eur: Optional[float] = None   # v3.0: 1 mese
    perf_3m_eur: Optional[float] = None   # v3.0: 3 mesi
    perf_6m_eur: Optional[float] = None   # v3.0: 6 mesi
    perf_ytd_eur: Optional[float] = None
    perf_1y_eur: Optional[float] = None
    perf_3y_eur: Optional[float] = None
    perf_5y_eur: Optional[float] = None
    perf_7y_eur: Optional[float] = None
    perf_9y_eur: Optional[float] = None   # v3.0: 9 anni
    perf_10y_eur: Optional[float] = None

    # Metriche rischio
    volatility_1y: Optional[float] = None
    volatility_3y: Optional[float] = None
    sharpe_ratio_3y: Optional[float] = None

    # Metadata
    sources: List[str] = field(default_factory=list)
    data_quality_score: float = 0.0
    last_updated: datetime = field(default_factory=datetime.now)

    def get_performance_by_period(self, period: str) -> Optional[float]:
        """Restituisce la performance per il periodo specificato."""
        mapping = {
            "1m": self.perf_1m_eur,
            "3m": self.perf_3m_eur,
            "6m": self.perf_6m_eur,
            "ytd": self.perf_ytd_eur,
            "1y": self.perf_1y_eur,
            "3y": self.perf_3y_eur,
            "5y": self.perf_5y_eur,
            "7y": self.perf_7y_eur,
            "9y": self.perf_9y_eur,
            "10y": self.perf_10y_eur,
        }
        return mapping.get(period)

    def to_dict(self) -> Dict[str, Any]:
        """Converte in dizionario per export."""
        return {
            "Nome": self.name,
            "ISIN": self.isin,
            "Tipo": self.instrument_type.value,
            "Valuta": self.currency,
            "Domicilio": self.domicile or "",
            "Distribuzione": self.distribution.value,
            "Cat. Morningstar": self.category_morningstar or "",
            "Cat. Assogestioni": self.category_assogestioni or "",
            "Perf. 1m": self.perf_1m_eur,
            "Perf. 3m": self.perf_3m_eur,
            "Perf. 6m": self.perf_6m_eur,
            "Perf. YTD": self.perf_ytd_eur,
            "Perf. 1a": self.perf_1y_eur,
            "Perf. 3a": self.perf_3y_eur,
            "Perf. 5a": self.perf_5y_eur,
            "Perf. 7a": self.perf_7y_eur,
            "Perf. 9a": self.perf_9y_eur,
            "Perf. 10a": self.perf_10y_eur,
            "Volatilita' 3a": self.volatility_3y,
            "Sharpe 3a": self.sharpe_ratio_3y,
            "Fonti": ", ".join(self.sources),
            "Qualita' Dati": f"{self.data_quality_score:.0f}%",
        }


@dataclass
class SearchCriteria:
    """
    Criteri di ricerca dall'interfaccia utente.

    Rappresenta i filtri selezionati dall'utente nella sidebar
    per la ricerca di fondi/ETF.
    """
    categories_morningstar: List[str] = field(default_factory=list)
    categories_assogestioni: List[str] = field(default_factory=list)
    currencies: List[str] = field(default_factory=lambda: ["EUR"])
    distribution_filter: Optional[DistributionPolicy] = None
    min_performance: Optional[float] = None
    performance_period: str = "3y"
    instrument_types: List[InstrumentType] = field(
        default_factory=lambda: [InstrumentType.ETF, InstrumentType.FUND]
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serializza per logging/caching."""
        return {
            "categories_ms": self.categories_morningstar,
            "categories_ag": self.categories_assogestioni,
            "currencies": self.currencies,
            "distribution": self.distribution_filter.value if self.distribution_filter else None,
            "min_perf": self.min_performance,
            "perf_period": self.performance_period,
            "types": [t.value for t in self.instrument_types],
        }

    def has_category_filter(self) -> bool:
        """Verifica se sono stati specificati filtri per categoria."""
        return bool(self.categories_morningstar or self.categories_assogestioni)


# =============================================================================
# MODELLI v3.0 - Universo Fondi e Confronto
# =============================================================================

@dataclass
class UniverseInstrument:
    """
    Strumento caricato dall'universo utente (file Excel).

    Rappresenta un fondo/strumento che l'utente ha nel proprio portafoglio
    con tutti i dati di performance, categoria e costi già inclusi.
    Formato supportato: export da piattaforme finanziarie con performance
    pre-calcolate (es. formato giada1.xlsx).
    """
    isin: str
    name: Optional[str] = None

    # Categorie
    category_morningstar: Optional[str] = None
    category_sfdr: Optional[str] = None

    # Performance (in percentuale, es. 0.0248 = 2.48%)
    perf_ytd: Optional[float] = None
    perf_1m: Optional[float] = None
    perf_3m: Optional[float] = None
    perf_6m: Optional[float] = None
    perf_1y: Optional[float] = None
    perf_3y: Optional[float] = None
    perf_5y: Optional[float] = None
    perf_7y: Optional[float] = None
    perf_9y: Optional[float] = None
    perf_10y: Optional[float] = None
    perf_custom: Optional[float] = None  # Perf. Personal.

    # Costi
    ter: Optional[float] = None  # Comm. Gest.+Distr.

    # Rischio
    var_3m: Optional[float] = None  # VaR Adeg. 3m
    market_price_5y: Optional[float] = None  # PR Mkt 5a

    # Metadati
    source_row: int = 0  # Riga nel file Excel originale

    def get_performance_by_period(self, period: str) -> Optional[float]:
        """
        Restituisce la performance per il periodo specificato.

        Args:
            period: Codice periodo (1m, 3m, 6m, ytd, 1y, 3y, 5y, 7y, 9y, 10y)

        Returns:
            Performance in percentuale o None
        """
        mapping = {
            "1m": self.perf_1m,
            "3m": self.perf_3m,
            "6m": self.perf_6m,
            "ytd": self.perf_ytd,
            "1y": self.perf_1y,
            "3y": self.perf_3y,
            "5y": self.perf_5y,
            "7y": self.perf_7y,
            "9y": self.perf_9y,
            "10y": self.perf_10y,
        }
        return mapping.get(period)

    def to_dict(self) -> Dict[str, Any]:
        """Converte in dizionario per export/display."""
        return {
            "ISIN": self.isin,
            "Nome": self.name or "",
            "Cat. Morningstar": self.category_morningstar or "",
            "Cat. SFDR": self.category_sfdr or "",
            "Perf. YTD": self._format_perf(self.perf_ytd),
            "Perf. 1m": self._format_perf(self.perf_1m),
            "Perf. 3m": self._format_perf(self.perf_3m),
            "Perf. 6m": self._format_perf(self.perf_6m),
            "Perf. 1a": self._format_perf(self.perf_1y),
            "Perf. 3a": self._format_perf(self.perf_3y),
            "Perf. 5a": self._format_perf(self.perf_5y),
            "Perf. 7a": self._format_perf(self.perf_7y),
            "Perf. 9a": self._format_perf(self.perf_9y),
            "Perf. 10a": self._format_perf(self.perf_10y),
            "TER": self._format_perf(self.ter),
            "VaR 3m": self._format_perf(self.var_3m),
        }

    def _format_perf(self, value: Optional[float]) -> Optional[str]:
        """Formatta percentuale per display."""
        if value is None:
            return None
        # Converti da decimale a percentuale (0.0248 -> 2.48%)
        return f"{value * 100:.2f}%"

    def to_aggregated(self) -> 'AggregatedInstrument':
        """
        Converte UniverseInstrument in AggregatedInstrument.

        Utile per uniformare i dati dell'universo con quelli di mercato
        per confronti e visualizzazioni.
        """
        return AggregatedInstrument(
            isin=self.isin,
            name=self.name or self.isin,
            instrument_type=InstrumentType.FUND,
            category_morningstar=self.category_morningstar,
            # Performance (converti da decimale a percentuale)
            perf_1m_eur=self.perf_1m * 100 if self.perf_1m is not None else None,
            perf_3m_eur=self.perf_3m * 100 if self.perf_3m is not None else None,
            perf_6m_eur=self.perf_6m * 100 if self.perf_6m is not None else None,
            perf_ytd_eur=self.perf_ytd * 100 if self.perf_ytd is not None else None,
            perf_1y_eur=self.perf_1y * 100 if self.perf_1y is not None else None,
            perf_3y_eur=self.perf_3y * 100 if self.perf_3y is not None else None,
            perf_5y_eur=self.perf_5y * 100 if self.perf_5y is not None else None,
            perf_7y_eur=self.perf_7y * 100 if self.perf_7y is not None else None,
            perf_9y_eur=self.perf_9y * 100 if self.perf_9y is not None else None,
            perf_10y_eur=self.perf_10y * 100 if self.perf_10y is not None else None,
            sources=["excel_upload"],
            data_quality_score=100.0,  # Dati completi da file
        )


@dataclass
class UniverseLoadResult:
    """
    Risultato del caricamento dell'universo fondi.

    Contiene sia gli strumenti validi che gli eventuali errori
    riscontrati durante il parsing del file Excel.
    """
    instruments: List[UniverseInstrument] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_rows: int = 0
    valid_count: int = 0
    invalid_count: int = 0

    @property
    def success(self) -> bool:
        """True se il caricamento ha prodotto almeno uno strumento valido."""
        return self.valid_count > 0 and len(self.errors) == 0


@dataclass
class ComparisonResult:
    """
    Risultato confronto singolo strumento.

    Contiene i dati aggregati dello strumento più i delta
    di performance rispetto al benchmark (ETF).
    """
    instrument: 'AggregatedInstrument'
    origin: str  # "universe" o "market"
    benchmark_isin: Optional[str] = None
    delta_1m: Optional[float] = None
    delta_3m: Optional[float] = None
    delta_6m: Optional[float] = None
    delta_ytd: Optional[float] = None
    delta_1y: Optional[float] = None
    delta_3y: Optional[float] = None
    delta_5y: Optional[float] = None
    delta_7y: Optional[float] = None
    delta_9y: Optional[float] = None
    delta_10y: Optional[float] = None

    def get_delta_by_period(self, period: str) -> Optional[float]:
        """Restituisce il delta per il periodo specificato."""
        mapping = {
            "1m": self.delta_1m,
            "3m": self.delta_3m,
            "6m": self.delta_6m,
            "ytd": self.delta_ytd,
            "1y": self.delta_1y,
            "3y": self.delta_3y,
            "5y": self.delta_5y,
            "7y": self.delta_7y,
            "9y": self.delta_9y,
            "10y": self.delta_10y,
        }
        return mapping.get(period)

    def is_outperformer(self, period: str = "3y", threshold: float = 0.5) -> Optional[bool]:
        """
        Verifica se lo strumento ha outperformato il benchmark.

        Args:
            period: Periodo di riferimento
            threshold: Soglia minima per considerare outperformance

        Returns:
            True se outperformer, False se underperformer, None se dati non disponibili
        """
        delta = self.get_delta_by_period(period)
        if delta is None:
            return None
        return delta > threshold

    def to_dict(self) -> Dict[str, Any]:
        """Converte in dizionario per DataFrame."""
        base = self.instrument.to_dict()
        base["Origine"] = self.origin
        base["Delta 1m"] = self.delta_1m
        base["Delta 3m"] = self.delta_3m
        base["Delta 6m"] = self.delta_6m
        base["Delta YTD"] = self.delta_ytd
        base["Delta 1a"] = self.delta_1y
        base["Delta 3a"] = self.delta_3y
        base["Delta 5a"] = self.delta_5y
        base["Delta 7a"] = self.delta_7y
        base["Delta 9a"] = self.delta_9y
        base["Delta 10a"] = self.delta_10y
        return base


@dataclass
class ComparisonReport:
    """
    Report completo del confronto.

    Contiene tutti i risultati del confronto più statistiche aggregate.
    """
    # Metadata
    comparison_type: str  # "universe_vs_etf" o "etf_vs_universe"
    category: Optional[str] = None
    category_type: Optional[str] = None  # "morningstar" o "assogestioni"
    benchmark_etf: Optional['AggregatedInstrument'] = None
    periods_analyzed: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    # Risultati
    results: List[ComparisonResult] = field(default_factory=list)

    # Statistiche
    total_instruments: int = 0
    universe_count: int = 0
    market_count: int = 0
    outperformers_count: int = 0
    underperformers_count: int = 0
    avg_delta: Dict[str, float] = field(default_factory=dict)
    best_performer: Optional[ComparisonResult] = None
    worst_performer: Optional[ComparisonResult] = None

    def calculate_statistics(self, reference_period: str = "3y") -> None:
        """
        Calcola le statistiche aggregate dai risultati.

        Args:
            reference_period: Periodo di riferimento per outperformer/underperformer
        """
        if not self.results:
            return

        self.total_instruments = len(self.results)
        self.universe_count = sum(1 for r in self.results if r.origin == "universe")
        self.market_count = sum(1 for r in self.results if r.origin == "market")

        # Calcola outperformer/underperformer
        universe_results = [r for r in self.results if r.origin == "universe"]
        self.outperformers_count = sum(
            1 for r in universe_results
            if r.is_outperformer(reference_period, threshold=0.5) is True
        )
        self.underperformers_count = sum(
            1 for r in universe_results
            if r.is_outperformer(reference_period, threshold=-0.5) is False
        )

        # Calcola media delta per ogni periodo
        periods = ["1m", "3m", "6m", "ytd", "1y", "3y", "5y", "7y", "9y", "10y"]
        for period in periods:
            deltas: List[float] = [
                d for d in (r.get_delta_by_period(period) for r in universe_results)
                if d is not None
            ]
            if deltas:
                self.avg_delta[period] = sum(deltas) / len(deltas)

        # Trova best/worst performer
        ref_deltas: List[tuple] = [
            (r, r.get_delta_by_period(reference_period))
            for r in universe_results
            if r.get_delta_by_period(reference_period) is not None
        ]
        if ref_deltas:
            ref_deltas.sort(key=lambda x: x[1] if x[1] is not None else 0.0, reverse=True)
            self.best_performer = ref_deltas[0][0]
            self.worst_performer = ref_deltas[-1][0]

    def to_dataframe(self):
        """Converte i risultati in DataFrame pandas."""
        import pandas as pd
        data = [r.to_dict() for r in self.results]
        return pd.DataFrame(data)
