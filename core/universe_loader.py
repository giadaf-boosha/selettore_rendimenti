"""
Universe Loader - Caricamento e validazione universo fondi da Excel.

Questo modulo gestisce il parsing dei file Excel contenenti l'elenco
dei fondi dell'utente (Universo Fondi) e la validazione dei codici ISIN.
"""
import re
import logging
from io import BytesIO
from typing import List, Optional

import pandas as pd

from core.models import UniverseInstrument, UniverseLoadResult
from config import UNIVERSE_MAX_ISINS, UNIVERSE_ALLOWED_EXTENSIONS

logger = logging.getLogger(__name__)

# Pattern ISIN: 2 lettere paese + 9 alfanumerici + 1 digit
ISIN_PATTERN = re.compile(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')


class UniverseLoader:
    """
    Carica e valida l'universo fondi da file Excel.

    Funzionalità:
    - Parsing file Excel (.xlsx, .xls)
    - Rilevamento automatico colonna ISIN
    - Validazione formato ISIN
    - Estrazione nome, categoria e note (opzionali)
    - Gestione errori e warning dettagliati
    """

    MAX_ISINS = UNIVERSE_MAX_ISINS
    ISIN_COLUMN_NAMES = ["isin", "ISIN", "Isin", "codice_isin", "codice isin", "cod_isin"]
    NAME_COLUMN_NAMES = ["nome", "name", "Nome", "Name", "denominazione", "Denominazione"]
    CATEGORY_COLUMN_NAMES = ["categoria", "category", "Categoria", "Category", "cat", "Cat"]
    NOTES_COLUMN_NAMES = ["note", "notes", "Note", "Notes", "commento", "Commento"]

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

        # Rileva colonna ISIN
        isin_col = self._detect_column(df, self.ISIN_COLUMN_NAMES)
        if not isin_col:
            result.errors.append(
                "Impossibile trovare colonna ISIN nel file. "
                f"Assicurati che il file contenga una colonna denominata: {', '.join(self.ISIN_COLUMN_NAMES[:3])}"
            )
            return result

        # Rileva altre colonne (opzionali)
        name_col = self._detect_column(df, self.NAME_COLUMN_NAMES)
        cat_col = self._detect_column(df, self.CATEGORY_COLUMN_NAMES)
        notes_col = self._detect_column(df, self.NOTES_COLUMN_NAMES)

        # Verifica limite ISIN
        if len(df) > self.MAX_ISINS:
            result.errors.append(
                f"Superato limite di {self.MAX_ISINS} ISIN. "
                f"Il file contiene {len(df)} righe."
            )
            return result

        # Processa ogni riga
        for row_idx, (_, row) in enumerate(df.iterrows()):
            row_num = row_idx + 2  # +2 per header e indice 0-based

            isin_raw = str(row.get(isin_col, "")).strip()

            # Normalizza ISIN
            isin = isin_raw.upper()

            # Valida ISIN
            if not isin:
                result.warnings.append(f"Riga {row_num}: ISIN vuoto, ignorata")
                result.invalid_count += 1
                continue

            if not self._validate_isin(isin):
                result.warnings.append(
                    f"Riga {row_num}: ISIN '{isin_raw}' non valido (formato: AA + 9 alfanum + 1 digit)"
                )
                result.invalid_count += 1
                continue

            # Estrai altri campi
            name = self._safe_string(row.get(name_col)) if name_col else None
            category = self._safe_string(row.get(cat_col)) if cat_col else None
            notes = self._safe_string(row.get(notes_col)) if notes_col else None

            instrument = UniverseInstrument(
                isin=isin,
                name=name,
                category=category,
                notes=notes,
                source_row=row_num
            )

            result.instruments.append(instrument)
            result.valid_count += 1

        # Log risultato
        logger.info(
            f"Universe loaded: {result.valid_count} valid, "
            f"{result.invalid_count} invalid, {len(result.warnings)} warnings"
        )

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

    def _detect_column(
        self,
        df: pd.DataFrame,
        possible_names: List[str]
    ) -> Optional[str]:
        """
        Rileva automaticamente una colonna dato un elenco di nomi possibili.

        Args:
            df: DataFrame
            possible_names: Lista nomi possibili per la colonna

        Returns:
            Nome colonna trovata o None
        """
        columns_lower = {col.lower().strip(): col for col in df.columns}

        for name in possible_names:
            name_lower = name.lower().strip()
            if name_lower in columns_lower:
                return columns_lower[name_lower]

        # Prova match parziale
        for name in possible_names:
            name_lower = name.lower().strip()
            for col_lower, col_original in columns_lower.items():
                if name_lower in col_lower or col_lower in name_lower:
                    return col_original

        return None

    def _validate_isin(self, isin: str) -> bool:
        """
        Valida formato ISIN.

        Formato: 2 lettere paese + 9 alfanumerici + 1 digit check
        Esempio: IE00B4L5Y983

        Args:
            isin: Codice ISIN (già uppercase)

        Returns:
            True se valido
        """
        if not isin or len(isin) != 12:
            return False
        return bool(ISIN_PATTERN.match(isin))

    def _safe_string(self, value) -> Optional[str]:
        """
        Converte valore in stringa, gestendo NaN/None.

        Args:
            value: Valore da convertire

        Returns:
            Stringa o None se vuoto/NaN
        """
        if pd.isna(value):
            return None
        s = str(value).strip()
        return s if s else None

    def _get_extension(self, filename: str) -> str:
        """Estrae l'estensione dal nome file."""
        if "." in filename:
            return "." + filename.rsplit(".", 1)[-1].lower()
        return ""


def validate_isin(isin: str) -> bool:
    """
    Funzione helper per validare un singolo ISIN.

    Args:
        isin: Codice ISIN da validare

    Returns:
        True se formato valido
    """
    if not isin or len(isin) != 12:
        return False
    isin_upper = isin.strip().upper()
    return bool(ISIN_PATTERN.match(isin_upper))


def get_unique_isins(instruments: List[UniverseInstrument]) -> List[str]:
    """
    Estrae lista di ISIN unici dagli strumenti.

    Args:
        instruments: Lista UniverseInstrument

    Returns:
        Lista ISIN unici
    """
    seen = set()
    result = []
    for inst in instruments:
        if inst.isin not in seen:
            seen.add(inst.isin)
            result.append(inst.isin)
    return result


def group_by_category(
    instruments: List[UniverseInstrument]
) -> dict:
    """
    Raggruppa strumenti per categoria.

    Args:
        instruments: Lista UniverseInstrument

    Returns:
        Dict categoria -> lista strumenti
    """
    groups: dict = {}
    for inst in instruments:
        cat = inst.category or "Senza Categoria"
        if cat not in groups:
            groups[cat] = []
        groups[cat].append(inst)
    return groups
