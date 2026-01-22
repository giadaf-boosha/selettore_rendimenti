"""
ETF Benchmark - Recupero dati ETF per confronto.

Questo modulo gestisce il recupero dei dati ETF per il confronto con
l'universo fondi dell'utente. Cerca prima nell'universo caricato,
poi su fonti esterne se necessario.
"""
from typing import Optional, List
from core.models import UniverseInstrument
from core.universe_loader import validate_isin
import logging

logger = logging.getLogger(__name__)


def find_etf_in_universe(
    isin: str,
    universe: List[UniverseInstrument]
) -> Optional[UniverseInstrument]:
    """
    Cerca l'ETF nell'universo caricato.

    Args:
        isin: ISIN dell'ETF da cercare
        universe: Lista strumenti dell'universo

    Returns:
        UniverseInstrument se trovato, None altrimenti
    """
    isin_upper = isin.strip().upper()

    for inst in universe:
        if inst.isin == isin_upper:
            return inst

    return None


def get_etf_from_external_sources(isin: str) -> Optional[dict]:
    """
    Recupera dati ETF da fonti esterne (Morningstar, JustETF).

    Args:
        isin: ISIN dell'ETF

    Returns:
        Dict con dati ETF o None se non trovato
    """
    # Prova Morningstar
    try:
        from scrapers.morningstar_scraper import MorningstarScraper
        scraper = MorningstarScraper()
        result = scraper.get_by_isin(isin)
        if result:
            logger.info(f"ETF {isin} trovato su Morningstar")
            return {
                "name": result.name,
                "category_morningstar": result.category_morningstar,
                "perf_ytd_eur": result.performance.ytd,
                "perf_1m_eur": result.performance.return_1m,
                "perf_3m_eur": result.performance.return_3m,
                "perf_6m_eur": result.performance.return_6m,
                "perf_1y_eur": result.performance.return_1y,
                "perf_3y_eur": result.performance.return_3y,
                "perf_5y_eur": result.performance.return_5y,
                "perf_7y_eur": result.performance.return_7y,
                "perf_9y_eur": result.performance.return_9y,
                "perf_10y_eur": result.performance.return_10y,
            }
    except Exception as e:
        logger.warning(f"Morningstar search failed for {isin}: {e}")

    # Prova JustETF
    try:
        from scrapers.justetf_scraper import JustETFScraper
        scraper = JustETFScraper()
        result = scraper.get_by_isin(isin)
        if result:
            logger.info(f"ETF {isin} trovato su JustETF")
            return {
                "name": result.name,
                "category_morningstar": result.category_morningstar,
                "perf_ytd_eur": result.performance.ytd,
                "perf_1m_eur": result.performance.return_1m,
                "perf_3m_eur": result.performance.return_3m,
                "perf_6m_eur": result.performance.return_6m,
                "perf_1y_eur": result.performance.return_1y,
                "perf_3y_eur": result.performance.return_3y,
                "perf_5y_eur": result.performance.return_5y,
                "perf_7y_eur": result.performance.return_7y,
                "perf_9y_eur": result.performance.return_9y,
                "perf_10y_eur": result.performance.return_10y,
            }
    except Exception as e:
        logger.warning(f"JustETF search failed for {isin}: {e}")

    return None


def get_etf_benchmark(
    isin: str,
    universe: List[UniverseInstrument]
) -> Optional[UniverseInstrument]:
    """
    Recupera dati ETF benchmark, prima dall'universo poi da fonti esterne.

    Args:
        isin: ISIN dell'ETF benchmark
        universe: Lista strumenti dell'universo

    Returns:
        UniverseInstrument con dati ETF o None se non trovato
    """
    # Valida formato ISIN
    if not validate_isin(isin):
        logger.warning(f"ISIN non valido: {isin}")
        return None

    # Prima cerca nell'universo (piu' veloce e dati consistenti)
    etf = find_etf_in_universe(isin, universe)
    if etf:
        logger.info(f"ETF {isin} trovato nell'universo: {etf.name}")
        return etf

    # Se non trovato, cerca su fonti esterne
    logger.info(f"ETF {isin} non nell'universo, cerco su fonti esterne...")
    external_data = get_etf_from_external_sources(isin)

    if external_data:
        # Converti in UniverseInstrument
        return UniverseInstrument(
            isin=isin.upper(),
            name=external_data.get("name", isin),
            category_morningstar=external_data.get("category_morningstar"),
            perf_ytd=external_data.get("perf_ytd_eur"),
            perf_1m=external_data.get("perf_1m_eur"),
            perf_3m=external_data.get("perf_3m_eur"),
            perf_6m=external_data.get("perf_6m_eur"),
            perf_1y=external_data.get("perf_1y_eur"),
            perf_3y=external_data.get("perf_3y_eur"),
            perf_5y=external_data.get("perf_5y_eur"),
            perf_7y=external_data.get("perf_7y_eur"),
            perf_9y=external_data.get("perf_9y_eur"),
            perf_10y=external_data.get("perf_10y_eur"),
        )

    logger.warning(f"ETF {isin} non trovato in nessuna fonte")
    return None
