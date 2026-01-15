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
    ytd: Optional[float] = None
    return_1y: Optional[float] = None
    return_3y: Optional[float] = None
    return_5y: Optional[float] = None
    return_7y: Optional[float] = None
    return_10y: Optional[float] = None

    def get_by_period(self, period: str) -> Optional[float]:
        """Restituisce la performance per il periodo specificato."""
        mapping = {
            "ytd": self.ytd,
            "1y": self.return_1y,
            "3y": self.return_3y,
            "5y": self.return_5y,
            "7y": self.return_7y,
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

    # Performance in EUR
    perf_ytd_eur: Optional[float] = None
    perf_1y_eur: Optional[float] = None
    perf_3y_eur: Optional[float] = None
    perf_5y_eur: Optional[float] = None
    perf_7y_eur: Optional[float] = None
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
            "ytd": self.perf_ytd_eur,
            "1y": self.perf_1y_eur,
            "3y": self.perf_3y_eur,
            "5y": self.perf_5y_eur,
            "7y": self.perf_7y_eur,
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
            "Perf. YTD": self.perf_ytd_eur,
            "Perf. 1a": self.perf_1y_eur,
            "Perf. 3a": self.perf_3y_eur,
            "Perf. 5a": self.perf_5y_eur,
            "Perf. 7a": self.perf_7y_eur,
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
