"""
Configurazione globale per Selettore Rendimenti Fondi/ETF.
"""
from dataclasses import dataclass, field
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()


@dataclass
class ScraperConfig:
    """Configurazione per singolo scraper."""
    enabled: bool = True
    rate_limit: float = 1.0
    timeout: int = 30
    max_retries: int = 3


@dataclass
class AppConfig:
    """Configurazione globale applicazione."""

    # Generale
    app_name: str = "Selettore Rendimenti Fondi/ETF"
    version: str = "3.1.0"
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_to_file: bool = True

    # Scrapers
    scrapers: Dict[str, ScraperConfig] = field(default_factory=dict)

    # Cache
    cache_ttl: int = int(os.getenv("CACHE_TTL", "3600"))

    # Export
    excel_max_rows: int = 10000

    def __post_init__(self):
        if not self.scrapers:
            self.scrapers = {
                "justetf": ScraperConfig(
                    enabled=True,
                    rate_limit=float(os.getenv("JUSTETF_RATE_LIMIT", "2.0")),
                    timeout=int(os.getenv("JUSTETF_TIMEOUT", "90")),
                ),
                "morningstar": ScraperConfig(
                    enabled=True,
                    # Increased from 0.5 to 2.0 to avoid rate limiting
                    rate_limit=float(os.getenv("MORNINGSTAR_RATE_LIMIT", "2.0")),
                    timeout=int(os.getenv("MORNINGSTAR_TIMEOUT", "60")),
                ),
                "investiny": ScraperConfig(
                    enabled=True,
                    rate_limit=float(os.getenv("INVESTINY_RATE_LIMIT", "2.0")),
                    timeout=int(os.getenv("INVESTINY_TIMEOUT", "60")),
                ),
            }


# Categorie Morningstar (principali per mercato italiano/europeo)
MORNINGSTAR_CATEGORIES: List[str] = [
    "Azionari Globali Large Cap Blend",
    "Azionari Globali Large Cap Growth",
    "Azionari Globali Large Cap Value",
    "Azionari USA Large Cap Blend",
    "Azionari USA Large Cap Growth",
    "Azionari USA Large Cap Value",
    "Azionari Europa Large Cap Blend",
    "Azionari Europa Large Cap Growth",
    "Azionari Europa Large Cap Value",
    "Azionari Italia",
    "Azionari Paesi Emergenti",
    "Azionari Asia-Pacifico ex-Giappone",
    "Azionari Giappone Large Cap",
    "Azionari Cina",
    "Azionari Settore Tecnologia",
    "Azionari Settore Salute",
    "Azionari Settore Energia",
    "Azionari Settore Finanza",
    "Azionari Settore Beni di Consumo",
    "Azionari Settore Immobiliare",
    "Azionari Settore Metalli Preziosi",
    "Azionari Settore Risorse Naturali",
    "Azionari Settore Infrastrutture",
    "Azionari Settore Utilities",
    "Obbligazionari EUR Diversificati",
    "Obbligazionari EUR Corporate",
    "Obbligazionari EUR High Yield",
    "Obbligazionari EUR Governativi",
    "Obbligazionari EUR Inflation-Linked",
    "Obbligazionari Globali",
    "Obbligazionari Globali High Yield",
    "Obbligazionari Mercati Emergenti",
    "Obbligazionari USD Corporate",
    "Obbligazionari USD High Yield",
    "Bilanciati EUR Prudenti",
    "Bilanciati EUR Moderati",
    "Bilanciati EUR Aggressivi",
    "Bilanciati Globali",
    "Flessibili EUR",
    "Flessibili Globali",
    "Alternativi - Multistrategy",
    "Alternativi - Long/Short Equity",
    "Monetari EUR",
]

# Categorie Assogestioni (classificazione italiana ufficiale)
ASSOGESTIONI_CATEGORIES: List[str] = [
    "AZ. AMERICA",
    "AZ. AREA EURO",
    "AZ. ENERGIA E MAT. PRIME",
    "AZ. EUROPA",
    "AZ. INTERNAZIONALI",
    "AZ. ITALIA",
    "AZ. PACIFICO",
    "AZ. PAESI EMERGENTI",
    "AZ. PAESE",
    "AZ. SALUTE",
    "AZ. SETTORIALI",
    "AZ. SETTORE TECNOLOGIA",
    "AZ. ALTRE SPECIALIZZAZIONI",
    "BILANCIATI",
    "BILANCIATI AZIONARI",
    "BILANCIATI OBBLIGAZIONARI",
    "FLESSIBILI",
    "OBBL. EURO CORPORATE INV. GRADE",
    "OBBL. EURO GOV. BREVE TERMINE",
    "OBBL. EURO GOV. M/L TERMINE",
    "OBBL. EURO HIGH YIELD",
    "OBBL. EURO MISTI",
    "OBBL. INTERNAZIONALI",
    "OBBL. INTERNAZIONALI GOV.",
    "OBBL. INTERNAZIONALI CORPORATE",
    "OBBL. PAESI EMERGENTI",
    "OBBL. ALTRE SPECIALIZZAZIONI",
    "FONDI DI LIQUIDITA' AREA EURO",
    "FONDI DI LIQUIDITA' ALTRE VALUTE",
]

# Valute supportate
CURRENCIES: List[str] = ["EUR", "USD", "GBP", "CHF"]

# Periodi performance (estesi per v3.0)
PERFORMANCE_PERIODS: Dict[str, str] = {
    "1 mese": "1m",
    "3 mesi": "3m",
    "6 mesi": "6m",
    "YTD": "ytd",
    "1 anno": "1y",
    "3 anni": "3y",
    "5 anni": "5y",
    "7 anni": "7y",
    "9 anni": "9y",
    "10 anni": "10y",
}

# Configurazione Universe Loader (v3.1)
# Increased to support larger files like giada1.xlsx with 3400+ instruments
# NOTE: Previous limit was 500, now 5000 to support full universe files
UNIVERSE_MAX_ISINS: int = 5000
UNIVERSE_ALLOWED_EXTENSIONS: List[str] = [".xlsx", ".xls"]

# Mapping categorie Assogestioni -> Morningstar per confronto
CATEGORY_MAPPING: Dict[str, List[str]] = {
    "AZ. AMERICA": ["Azionari USA Large Cap Blend", "Azionari USA Large Cap Growth", "Azionari USA Large Cap Value"],
    "AZ. AREA EURO": ["Azionari Europa Large Cap Blend", "Azionari Eurozona Large Cap"],
    "AZ. EUROPA": ["Azionari Europa Large Cap Blend", "Azionari Europa Large Cap Growth", "Azionari Europa Large Cap Value"],
    "AZ. INTERNAZIONALI": ["Azionari Globali Large Cap Blend", "Azionari Globali Large Cap Growth", "Azionari Globali Large Cap Value"],
    "AZ. ITALIA": ["Azionari Italia"],
    "AZ. PACIFICO": ["Azionari Asia-Pacifico ex-Giappone", "Azionari Giappone Large Cap"],
    "AZ. PAESI EMERGENTI": ["Azionari Paesi Emergenti"],
    "AZ. SETTORE TECNOLOGIA": ["Azionari Settore Tecnologia"],
    "AZ. SALUTE": ["Azionari Settore Salute"],
    "AZ. ENERGIA E MAT. PRIME": ["Azionari Settore Energia", "Azionari Settore Risorse Naturali"],
    "BILANCIATI": ["Bilanciati EUR Moderati", "Bilanciati Globali"],
    "BILANCIATI AZIONARI": ["Bilanciati EUR Aggressivi"],
    "BILANCIATI OBBLIGAZIONARI": ["Bilanciati EUR Prudenti"],
    "FLESSIBILI": ["Flessibili EUR", "Flessibili Globali"],
    "OBBL. EURO CORPORATE INV. GRADE": ["Obbligazionari EUR Corporate"],
    "OBBL. EURO GOV. BREVE TERMINE": ["Obbligazionari EUR Governativi"],
    "OBBL. EURO GOV. M/L TERMINE": ["Obbligazionari EUR Governativi", "Obbligazionari EUR Diversificati"],
    "OBBL. EURO HIGH YIELD": ["Obbligazionari EUR High Yield"],
    "OBBL. EURO MISTI": ["Obbligazionari EUR Diversificati"],
    "OBBL. INTERNAZIONALI": ["Obbligazionari Globali"],
    "OBBL. INTERNAZIONALI GOV.": ["Obbligazionari Globali"],
    "OBBL. INTERNAZIONALI CORPORATE": ["Obbligazionari USD Corporate"],
    "OBBL. PAESI EMERGENTI": ["Obbligazionari Mercati Emergenti"],
    "FONDI DI LIQUIDITA' AREA EURO": ["Monetari EUR"],
}

# Istanza configurazione globale
config = AppConfig()
