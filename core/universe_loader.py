"""
Universe Loader - Caricamento e validazione universo fondi da Excel.

Questo modulo gestisce il parsing dei file Excel contenenti l'elenco
dei fondi dell'utente (Universo Fondi) con dati di performance completi.

Formato supportato (es. giada1.xlsx):
- Nome: Nome del fondo
- Isin: Codice ISIN
- Perf. YTD (EUR), Perf. 1m (EUR), ... Perf. 10a (EUR): Performance
- Comm. Gest.+Distr.: TER/Commissioni
- Categoria Morningstar: Categoria Morningstar
- Categoria SFDR: Classificazione SFDR
- VaR Adeg. 3m: Value at Risk
"""
import re
import logging
from io import BytesIO
from typing import List, Optional, Dict, Any

import pandas as pd

from core.models import UniverseInstrument, UniverseLoadResult
from config import UNIVERSE_MAX_ISINS, UNIVERSE_ALLOWED_EXTENSIONS

logger = logging.getLogger(__name__)

# Pattern ISIN: 2 lettere paese + 9 alfanumerici + 1 digit
ISIN_PATTERN = re.compile(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')


class UniverseLoader:
    """
    Carica e valida l'universo fondi da file Excel.

    Supporta file Excel con dati completi di performance, categorie e costi.
    Rileva automaticamente le colonne e mappa i dati al modello UniverseInstrument.
    """

    MAX_ISINS = UNIVERSE_MAX_ISINS

    # Mapping colonne Excel -> attributi modello
    # Formato: nome_attributo -> lista possibili nomi colonne
    COLUMN_MAPPINGS: Dict[str, List[str]] = {
        "isin": ["isin", "ISIN", "Isin", "codice_isin", "codice isin", "cod_isin"],
        "name": ["nome", "name", "Nome", "Name", "denominazione", "Denominazione"],
        "category_morningstar": [
            "categoria morningstar", "Categoria Morningstar", "cat morningstar",
            "Cat. Morningstar", "morningstar category"
        ],
        "category_sfdr": [
            "categoria sfdr", "Categoria SFDR", "Categoria  SFDR",
            "cat sfdr", "SFDR", "sfdr"
        ],
        "perf_ytd": [
            "perf. ytd  (eur)", "Perf. YTD  (EUR)", "perf. ytd (eur)",
            "Perf. YTD (EUR)", "ytd", "YTD", "perf ytd"
        ],
        "perf_1m": [
            "perf. 1m  (eur)", "Perf. 1m  (EUR)", "perf. 1m (eur)",
            "Perf. 1m (EUR)", "1m", "perf 1m"
        ],
        "perf_3m": [
            "perf. 3m  (eur)", "Perf. 3m  (EUR)", "perf. 3m (eur)",
            "Perf. 3m (EUR)", "3m", "perf 3m"
        ],
        "perf_6m": [
            "perf. 6m  (eur)", "Perf. 6m  (EUR)", "perf. 6m (eur)",
            "Perf. 6m (EUR)", "6m", "perf 6m"
        ],
        "perf_1y": [
            "perf. 1a  (eur)", "Perf. 1a  (EUR)", "perf. 1a (eur)",
            "Perf. 1a (EUR)", "1a", "1y", "perf 1a", "perf 1y"
        ],
        "perf_3y": [
            "perf. 3a  (eur)", "Perf. 3a  (EUR)", "perf. 3a (eur)",
            "Perf. 3a (EUR)", "3a", "3y", "perf 3a", "perf 3y"
        ],
        "perf_5y": [
            "perf. 5a  (eur)", "Perf. 5a  (EUR)", "perf. 5a (eur)",
            "Perf. 5a (EUR)", "5a", "5y", "perf 5a", "perf 5y"
        ],
        "perf_7y": [
            "perf. 7a  (eur)", "Perf. 7a  (EUR)", "perf. 7a (eur)",
            "Perf. 7a (EUR)", "7a", "7y", "perf 7a", "perf 7y"
        ],
        "perf_9y": [
            "perf. 9a  (eur)", "Perf. 9a  (EUR)", "perf. 9a (eur)",
            "Perf. 9a (EUR)", "9a", "9y", "perf 9a", "perf 9y"
        ],
        "perf_10y": [
            "perf. 10a  (eur)", "Perf. 10a  (EUR)", "perf. 10a (eur)",
            "Perf. 10a (EUR)", "10a", "10y", "perf 10a", "perf 10y"
        ],
        "perf_custom": [
            "perf. personal. (eur)", "Perf. Personal. (EUR)",
            "perf personal", "personalizzata"
        ],
        "ter": [
            "comm. gest.+distr.", "Comm. Gest.+Distr.", "ter", "TER",
            "commissioni", "expense ratio", "ongoing charge"
        ],
        "var_3m": [
            "var adeg.  3m", "VaR Adeg.  3m", "var adeg. 3m",
            "VaR Adeg. 3m", "var 3m", "VaR 3m", "var"
        ],
        "market_price_5y": [
            "pr mkt 5a  (eur)", "PR Mkt 5a  (EUR)", "pr mkt 5a (eur)",
            "PR Mkt 5a (EUR)", "market price 5y"
        ],
    }

    def load(self, file: BytesIO, filename: str = "") -> UniverseLoadResult:
        """
        Carica universo da file Excel.

        Args:
            file: BytesIO con contenuto file Excel
            filename: Nome originale del file (per messaggi errore)

        Returns:
            UniverseLoadResult con instruments validi e errori
        """
        result = UniverseLoadResult()

        # Verifica estensione
        if filename:
            ext = self._get_extension(filename)
            if ext not in UNIVERSE_ALLOWED_EXTENSIONS:
                result.errors.append(
                    f"Formato file non supportato: {ext}. "
                    f"Usa: {', '.join(UNIVERSE_ALLOWED_EXTENSIONS)}"
                )
                return result

        # Parse Excel
        try:
            df = self._parse_excel(file)
        except Exception as e:
            result.errors.append(f"Errore lettura file Excel: {str(e)}")
            return result

        if df.empty:
            result.errors.append("Il file non contiene dati")
            return result

        result.total_rows = len(df)

        # Rileva tutte le colonne
        column_map = self._detect_all_columns(df)

        # Verifica colonna ISIN (obbligatoria)
        if "isin" not in column_map:
            result.errors.append(
                "Impossibile trovare colonna ISIN nel file. "
                "Assicurati che il file contenga una colonna denominata 'ISIN' o 'Isin'."
            )
            return result

        # Verifica limite ISIN
        if len(df) > self.MAX_ISINS:
            result.errors.append(
                f"Superato limite di {self.MAX_ISINS} ISIN. "
                f"Il file contiene {len(df)} righe."
            )
            return result

        # Log delle colonne rilevate
        detected_cols = list(column_map.keys())
        logger.info(f"Colonne rilevate: {detected_cols}")

        # Processa ogni riga
        for row_idx, (_, row) in enumerate(df.iterrows()):
            row_num = row_idx + 2  # +2 per header e indice 0-based

            # Estrai ISIN
            isin_raw = str(row.get(column_map["isin"], "")).strip()
            isin = isin_raw.upper()

            # Valida ISIN
            if not isin:
                result.warnings.append(f"Riga {row_num}: ISIN vuoto, ignorata")
                result.invalid_count += 1
                continue

            if not self._validate_isin(isin):
                result.warnings.append(
                    f"Riga {row_num}: ISIN '{isin_raw}' non valido"
                )
                result.invalid_count += 1
                continue

            # Crea UniverseInstrument con tutti i campi
            instrument = self._row_to_instrument(row, column_map, isin, row_num)

            result.instruments.append(instrument)
            result.valid_count += 1

        # Log risultato
        logger.info(
            f"Universe loaded: {result.valid_count} valid, "
            f"{result.invalid_count} invalid, {len(result.warnings)} warnings"
        )

        return result

    def _row_to_instrument(
        self,
        row: pd.Series,
        column_map: Dict[str, str],
        isin: str,
        row_num: int
    ) -> UniverseInstrument:
        """
        Converte una riga DataFrame in UniverseInstrument.

        Args:
            row: Riga del DataFrame
            column_map: Mapping attributo -> nome colonna
            isin: ISIN validato
            row_num: Numero riga nel file

        Returns:
            UniverseInstrument popolato
        """
        def get_str(attr: str) -> Optional[str]:
            if attr not in column_map:
                return None
            return self._safe_string(row.get(column_map[attr]))

        def get_float(attr: str) -> Optional[float]:
            if attr not in column_map:
                return None
            return self._safe_float(row.get(column_map[attr]))

        return UniverseInstrument(
            isin=isin,
            name=get_str("name"),
            category_morningstar=get_str("category_morningstar"),
            category_sfdr=get_str("category_sfdr"),
            perf_ytd=get_float("perf_ytd"),
            perf_1m=get_float("perf_1m"),
            perf_3m=get_float("perf_3m"),
            perf_6m=get_float("perf_6m"),
            perf_1y=get_float("perf_1y"),
            perf_3y=get_float("perf_3y"),
            perf_5y=get_float("perf_5y"),
            perf_7y=get_float("perf_7y"),
            perf_9y=get_float("perf_9y"),
            perf_10y=get_float("perf_10y"),
            perf_custom=get_float("perf_custom"),
            ter=get_float("ter"),
            var_3m=get_float("var_3m"),
            market_price_5y=get_float("market_price_5y"),
            source_row=row_num,
        )

    def _detect_all_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Rileva automaticamente tutte le colonne mappabili.

        Args:
            df: DataFrame da analizzare

        Returns:
            Dict attributo -> nome colonna trovata
        """
        result: Dict[str, str] = {}
        columns_lower = {col.lower().strip(): col for col in df.columns}

        for attr, possible_names in self.COLUMN_MAPPINGS.items():
            for name in possible_names:
                name_lower = name.lower().strip()
                if name_lower in columns_lower:
                    result[attr] = columns_lower[name_lower]
                    break

            # Se non trovato, prova match parziale
            if attr not in result:
                for name in possible_names:
                    name_lower = name.lower().strip()
                    for col_lower, col_original in columns_lower.items():
                        if name_lower in col_lower or col_lower in name_lower:
                            result[attr] = col_original
                            break
                    if attr in result:
                        break

        return result

    def _parse_excel(self, file: BytesIO) -> pd.DataFrame:
        """
        Parse file Excel in DataFrame.

        Prova prima .xlsx poi .xls se necessario.
        """
        file.seek(0)
        try:
            # Prova formato xlsx
            return pd.read_excel(file, engine='openpyxl')
        except Exception:
            file.seek(0)
            try:
                # Fallback a xlrd per .xls
                return pd.read_excel(file, engine='xlrd')
            except Exception:
                file.seek(0)
                # Ultimo tentativo senza specificare engine
                return pd.read_excel(file)

    def _validate_isin(self, isin: str) -> bool:
        """
        Valida formato ISIN.

        Formato: 2 lettere paese + 9 alfanumerici + 1 digit check
        Esempio: IE00B4L5Y983
        """
        if not isin or len(isin) != 12:
            return False
        return bool(ISIN_PATTERN.match(isin))

    def _safe_string(self, value: Any) -> Optional[str]:
        """
        Converte valore in stringa, gestendo NaN/None.
        """
        if pd.isna(value):
            return None
        s = str(value).strip()
        if s == "-" or s == "":
            return None
        return s

    def _safe_float(self, value: Any) -> Optional[float]:
        """
        Converte valore in float, gestendo NaN/None e stringhe.
        """
        if pd.isna(value):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            s = value.strip()
            if s == "-" or s == "":
                return None
            try:
                # Gestisce formati europei (virgola come decimale)
                s = s.replace(",", ".")
                # Rimuovi percentuali
                s = s.replace("%", "")
                return float(s)
            except ValueError:
                return None
        return None

    def _get_extension(self, filename: str) -> str:
        """Estrae l'estensione dal nome file."""
        if "." in filename:
            return "." + filename.rsplit(".", 1)[-1].lower()
        return ""


def validate_isin(isin: str) -> bool:
    """
    Funzione helper per validare un singolo ISIN.
    """
    if not isin or len(isin) != 12:
        return False
    isin_upper = isin.strip().upper()
    return bool(ISIN_PATTERN.match(isin_upper))


def get_unique_isins(instruments: List[UniverseInstrument]) -> List[str]:
    """
    Estrae lista di ISIN unici dagli strumenti.
    """
    seen = set()
    result = []
    for inst in instruments:
        if inst.isin not in seen:
            seen.add(inst.isin)
            result.append(inst.isin)
    return result


def group_by_category(instruments: List[UniverseInstrument]) -> dict:
    """
    Raggruppa strumenti per categoria Morningstar.
    """
    groups: dict = {}
    for inst in instruments:
        cat = inst.category_morningstar or "Senza Categoria"
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(inst)
    return groups


def filter_by_performance(
    instruments: List[UniverseInstrument],
    period: str,
    min_value: Optional[float] = None,
    max_value: Optional[float] = None
) -> List[UniverseInstrument]:
    """
    Filtra strumenti per performance nel periodo specificato.

    Args:
        instruments: Lista strumenti
        period: Codice periodo (1m, 3m, 6m, ytd, 1y, 3y, 5y, 7y, 9y, 10y)
        min_value: Performance minima (in decimale, es. 0.05 = 5%)
        max_value: Performance massima

    Returns:
        Lista strumenti filtrati
    """
    result = []
    for inst in instruments:
        perf = inst.get_performance_by_period(period)
        if perf is None:
            continue
        if min_value is not None and perf < min_value:
            continue
        if max_value is not None and perf > max_value:
            continue
        result.append(inst)
    return result


def rank_by_performance(
    instruments: List[UniverseInstrument],
    period: str,
    ascending: bool = False,
    top_n: Optional[int] = None
) -> List[UniverseInstrument]:
    """
    Ordina strumenti per performance nel periodo specificato.

    Args:
        instruments: Lista strumenti
        period: Codice periodo
        ascending: Se True, ordina dal peggiore al migliore
        top_n: Se specificato, restituisce solo i primi N

    Returns:
        Lista strumenti ordinata
    """
    # Filtra strumenti con performance valida
    valid = [(inst, inst.get_performance_by_period(period))
             for inst in instruments
             if inst.get_performance_by_period(period) is not None]

    # Ordina
    sorted_list = sorted(valid, key=lambda x: x[1] or 0, reverse=not ascending)

    # Estrai strumenti
    result = [inst for inst, _ in sorted_list]

    if top_n is not None:
        return result[:top_n]
    return result
