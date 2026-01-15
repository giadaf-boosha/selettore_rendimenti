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
    version: str = "1.0.0"
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
                    rate_limit=float(os.getenv("JUSTETF_RATE_LIMIT", "1.0")),
                    timeout=int(os.getenv("JUSTETF_TIMEOUT", "60")),
                ),
                "morningstar": ScraperConfig(
                    enabled=True,
                    rate_limit=float(os.getenv("MORNINGSTAR_RATE_LIMIT", "0.5")),
                    timeout=int(os.getenv("MORNINGSTAR_TIMEOUT", "30")),
                ),
                "investiny": ScraperConfig(
                    enabled=True,
                    rate_limit=float(os.getenv("INVESTINY_RATE_LIMIT", "1.0")),
                    timeout=int(os.getenv("INVESTINY_TIMEOUT", "30")),
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

# Periodi performance
PERFORMANCE_PERIODS: Dict[str, str] = {
    "YTD": "ytd",
    "1 anno": "1y",
    "3 anni": "3y",
    "5 anni": "5y",
    "7 anni": "7y",
    "10 anni": "10y",
}

# Istanza configurazione globale
config = AppConfig()
