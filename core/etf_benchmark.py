"""
ETF Benchmark - Recupero dati ETF per confronto.

Questo modulo gestisce il recupero dei dati ETF per il confronto con
l'universo fondi dell'utente. Cerca prima nell'universo caricato,
poi nella cache locale, poi su fonti esterne se necessario.
"""
from typing import Optional, List, Dict
from time import time
from core.models import UniverseInstrument
from core.universe_loader import validate_isin
import logging

logger = logging.getLogger(__name__)

# Cache locale per ETF pre-caricati
# Struttura: {isin: {'data': UniverseInstrument, 'timestamp': float}}
_etf_cache: Dict[str, dict] = {}
_cache_ttl: int = 86400  # 24 ore


def get_etf_cache_status() -> dict:
    """
    Restituisce lo stato della cache ETF locale.

    Returns:
        dict con: count (int), isins (list), expires_in_minutes (int o None)
    """
    now = time()
    valid_entries = {}

    for isin, entry in _etf_cache.items():
        if now - entry['timestamp'] < _cache_ttl:
            valid_entries[isin] = entry

    # Pulisci cache scaduta
    _etf_cache.clear()
    _etf_cache.update(valid_entries)

    if valid_entries:
        # Trova il tempo rimanente minimo
        oldest_timestamp = min(e['timestamp'] for e in valid_entries.values())
        remaining = _cache_ttl - (now - oldest_timestamp)
        return {
            'count': len(valid_entries),
            'isins': list(valid_entries.keys()),
            'expires_in_minutes': max(0, int(remaining / 60)),
        }

    return {
        'count': 0,
        'isins': [],
        'expires_in_minutes': None,
    }


def find_etf_in_cache(isin: str) -> Optional[UniverseInstrument]:
    """
    Cerca l'ETF nella cache locale.

    Args:
        isin: ISIN dell'ETF da cercare

    Returns:
        UniverseInstrument se trovato e non scaduto, None altrimenti
    """
    isin_upper = isin.strip().upper()
    entry = _etf_cache.get(isin_upper)

    if entry:
        if time() - entry['timestamp'] < _cache_ttl:
            logger.debug(f"ETF {isin_upper} trovato in cache locale")
            return entry['data']
        else:
            # Cache scaduta, rimuovi
            del _etf_cache[isin_upper]

    return None


def add_etf_to_cache(isin: str, etf_data: UniverseInstrument) -> None:
    """
    Aggiunge un ETF alla cache locale.

    Args:
        isin: ISIN dell'ETF
        etf_data: Dati dell'ETF
    """
    isin_upper = isin.strip().upper()
    _etf_cache[isin_upper] = {
        'data': etf_data,
        'timestamp': time(),
    }
    logger.info(f"ETF {isin_upper} aggiunto alla cache locale")


def clear_etf_cache() -> None:
    """Svuota la cache ETF locale."""
    _etf_cache.clear()
    logger.info("Cache ETF locale svuotata")


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


def _has_useful_performance(result) -> bool:
    """
    Verifica se il risultato ha almeno una performance utile (1y, 3y o 5y).

    Questo evita di accettare risultati che hanno solo metadati ma nessuna
    performance, permettendo di provare altre fonti.
    """
    if not result or not result.performance:
        return False
    perf = result.performance
    return any([
        perf.return_1y is not None,
        perf.return_3y is not None,
        perf.return_5y is not None,
    ])


def get_etf_from_external_sources(isin: str) -> Optional[dict]:
    """
    Recupera dati ETF da fonti esterne (Morningstar, JustETF).

    Priorità: JustETF (dati più completi per ETF) > Morningstar.
    Se una fonte non ha performance utili, prova la successiva.

    Args:
        isin: ISIN dell'ETF

    Returns:
        Dict con dati ETF o None se non trovato
    """
    # Prova prima JustETF (fonte primaria per ETF con dati più completi)
    try:
        from scrapers.justetf_scraper import JustETFScraper
        scraper = JustETFScraper()
        result = scraper.get_by_isin(isin)
        if result and _has_useful_performance(result):
            logger.info(f"ETF {isin} trovato su JustETF con performance")
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
        elif result:
            logger.info(f"ETF {isin} trovato su JustETF ma senza performance utili")
    except Exception as e:
        logger.warning(f"JustETF search failed for {isin}: {e}")

    # Fallback a Morningstar
    try:
        from scrapers.morningstar_scraper import MorningstarScraper
        scraper = MorningstarScraper()
        result = scraper.get_by_isin(isin)
        if result and _has_useful_performance(result):
            logger.info(f"ETF {isin} trovato su Morningstar con performance")
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
        elif result:
            logger.info(f"ETF {isin} trovato su Morningstar ma senza performance utili")
    except Exception as e:
        logger.warning(f"Morningstar search failed for {isin}: {e}")

    return None


def get_etf_benchmark(
    isin: str,
    universe: List[UniverseInstrument],
    use_cache: bool = True
) -> Optional[UniverseInstrument]:
    """
    Recupera dati ETF benchmark.

    Ordine di ricerca:
    1. Universo caricato (istantaneo)
    2. Cache locale (istantaneo, se pre-caricato)
    3. Fonti esterne (lento, ~2-5 sec)

    Args:
        isin: ISIN dell'ETF benchmark
        universe: Lista strumenti dell'universo
        use_cache: Se True, cerca anche nella cache locale

    Returns:
        UniverseInstrument con dati ETF o None se non trovato
    """
    # Valida formato ISIN
    if not validate_isin(isin):
        logger.warning(f"ISIN non valido: {isin}")
        return None

    isin_upper = isin.strip().upper()

    # 1. Cerca nell'universo (piu' veloce e dati consistenti)
    etf = find_etf_in_universe(isin_upper, universe)
    if etf:
        logger.info(f"ETF {isin_upper} trovato nell'universo: {etf.name}")
        return etf

    # 2. Cerca nella cache locale (se abilitata)
    if use_cache:
        etf = find_etf_in_cache(isin_upper)
        if etf:
            logger.info(f"ETF {isin_upper} trovato in cache: {etf.name}")
            return etf

    # 3. Cerca su fonti esterne
    logger.info(f"ETF {isin_upper} non in universo/cache, cerco su fonti esterne...")
    external_data = get_etf_from_external_sources(isin_upper)

    if external_data:
        # Converti in UniverseInstrument
        etf = UniverseInstrument(
            isin=isin_upper,
            name=external_data.get("name", isin_upper),
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

        # Salva in cache per usi futuri
        add_etf_to_cache(isin_upper, etf)
        return etf

    logger.warning(f"ETF {isin_upper} non trovato in nessuna fonte")
    return None


def preload_etf_list(isins: List[str]) -> dict:
    """
    Pre-carica una lista di ETF nella cache locale.

    Args:
        isins: Lista di ISIN da pre-caricare

    Returns:
        dict con: loaded (list), failed (list), total (int)
    """
    loaded = []
    failed = []

    for isin in isins:
        isin_clean = isin.strip().upper()
        if not isin_clean:
            continue

        if not validate_isin(isin_clean):
            failed.append({'isin': isin_clean, 'reason': 'ISIN non valido'})
            continue

        # Controlla se già in cache
        if find_etf_in_cache(isin_clean):
            loaded.append({'isin': isin_clean, 'name': _etf_cache[isin_clean]['data'].name, 'cached': True})
            continue

        # Cerca su fonti esterne
        external_data = get_etf_from_external_sources(isin_clean)

        if external_data:
            etf = UniverseInstrument(
                isin=isin_clean,
                name=external_data.get("name", isin_clean),
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
            add_etf_to_cache(isin_clean, etf)
            loaded.append({'isin': isin_clean, 'name': etf.name, 'cached': False})
        else:
            failed.append({'isin': isin_clean, 'reason': 'Non trovato'})

    return {
        'loaded': loaded,
        'failed': failed,
        'total': len(loaded),
    }
