"""
Selettore Automatico Rendimenti Fondi/ETF v3.1

Web application Streamlit per l'analisi e il ranking di fondi comuni
a partire da file Excel con dati di performance completi.

Funzionalita' v3.1:
- Upload Universo Fondi da Excel (formato completo con performance)
- Esplorazione e filtering per categoria, performance, TER
- Ranking per periodo di performance
- Confronto tra fondi della stessa categoria
- Export risultati in Excel

Autore: Boosha AI
Cliente: Massimo Zaffanella - Consulente Finanziario
Versione: 3.1.0
"""
# IMPORTANT: Import http_config FIRST to patch requests library
# This adds realistic User-Agent headers to avoid bot detection
import utils.http_config  # noqa: F401 - patches requests on import

import streamlit as st
import pandas as pd
from datetime import datetime
import logging
import sys
from pathlib import Path
from io import BytesIO
from typing import List, Optional

# Aggiungi la directory corrente al path per gli import
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    PERFORMANCE_PERIODS,
    config,
)
from core.models import UniverseInstrument
from core.universe_loader import (
    UniverseLoader,
    group_by_category,
    filter_by_performance,
    rank_by_performance,
)
from utils.logger import setup_logging

# Setup logging
setup_logging(level=config.log_level, log_file=False)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURAZIONE PAGINA
# ============================================================================

st.set_page_config(
    page_title="Selettore Rendimenti Fondi/ETF v3.1",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': f"Selettore Automatico Rendimenti - v{config.version} | Boosha AI"
    }
)


# ============================================================================
# INIZIALIZZAZIONE SESSION STATE
# ============================================================================

def init_session_state():
    """Inizializza le variabili di session state."""
    defaults = {
        # Stato universo
        'universe_loaded': False,
        'universe_instruments': [],
        'universe_load_result': None,
        'universe_filename': None,
        # Stato filtri e risultati
        'filtered_instruments': [],
        'filter_applied': False,
        # Modalita' attiva
        'active_mode': 'esplora',
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


init_session_state()


# ============================================================================
# FUNZIONI HELPER
# ============================================================================

@st.cache_resource
def get_universe_loader():
    """Restituisce istanza cached dell'universe loader."""
    return UniverseLoader()


def load_universe(uploaded_file):
    """Carica l'universo fondi da file Excel."""
    try:
        loader = get_universe_loader()
        file_bytes = BytesIO(uploaded_file.getvalue())
        result = loader.load(file_bytes, uploaded_file.name)

        st.session_state.universe_load_result = result
        st.session_state.universe_instruments = result.instruments
        st.session_state.universe_loaded = result.success or result.valid_count > 0
        st.session_state.universe_filename = uploaded_file.name
        st.session_state.filtered_instruments = result.instruments
        st.session_state.filter_applied = False

        logger.info(f"Universe loaded: {result.valid_count} instruments")
        return result

    except Exception as e:
        logger.error(f"Universe load failed: {e}")
        st.session_state.universe_loaded = False
        st.session_state.universe_instruments = []
        return None


def universe_to_dataframe(instruments: List[UniverseInstrument]) -> pd.DataFrame:
    """Converte lista di UniverseInstrument in DataFrame per visualizzazione."""
    if not instruments:
        return pd.DataFrame()

    data = []
    for inst in instruments:
        row = {
            "Nome": inst.name or inst.isin,
            "ISIN": inst.isin,
            "Cat. Morningstar": inst.category_morningstar or "",
            "Cat. SFDR": inst.category_sfdr or "",
        }

        # Performance (converti da decimale a percentuale)
        if inst.perf_ytd is not None:
            row["Perf. YTD"] = f"{inst.perf_ytd * 100:.2f}%"
        else:
            row["Perf. YTD"] = ""

        if inst.perf_1m is not None:
            row["Perf. 1m"] = f"{inst.perf_1m * 100:.2f}%"
        else:
            row["Perf. 1m"] = ""

        if inst.perf_3m is not None:
            row["Perf. 3m"] = f"{inst.perf_3m * 100:.2f}%"
        else:
            row["Perf. 3m"] = ""

        if inst.perf_6m is not None:
            row["Perf. 6m"] = f"{inst.perf_6m * 100:.2f}%"
        else:
            row["Perf. 6m"] = ""

        if inst.perf_1y is not None:
            row["Perf. 1a"] = f"{inst.perf_1y * 100:.2f}%"
        else:
            row["Perf. 1a"] = ""

        if inst.perf_3y is not None:
            row["Perf. 3a"] = f"{inst.perf_3y * 100:.2f}%"
        else:
            row["Perf. 3a"] = ""

        if inst.perf_5y is not None:
            row["Perf. 5a"] = f"{inst.perf_5y * 100:.2f}%"
        else:
            row["Perf. 5a"] = ""

        if inst.perf_7y is not None:
            row["Perf. 7a"] = f"{inst.perf_7y * 100:.2f}%"
        else:
            row["Perf. 7a"] = ""

        if inst.perf_9y is not None:
            row["Perf. 9a"] = f"{inst.perf_9y * 100:.2f}%"
        else:
            row["Perf. 9a"] = ""

        if inst.perf_10y is not None:
            row["Perf. 10a"] = f"{inst.perf_10y * 100:.2f}%"
        else:
            row["Perf. 10a"] = ""

        if inst.ter is not None:
            row["TER"] = f"{inst.ter * 100:.2f}%"
        else:
            row["TER"] = ""

        if inst.var_3m is not None:
            row["VaR 3m"] = f"{inst.var_3m * 100:.2f}%"
        else:
            row["VaR 3m"] = ""

        data.append(row)

    return pd.DataFrame(data)


def universe_to_excel(instruments: List[UniverseInstrument]) -> bytes:
    """Esporta lista di strumenti in formato Excel."""
    df = universe_to_dataframe(instruments)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Fondi', index=False)

        # Auto-adjust column widths
        worksheet = writer.sheets['Fondi']
        for idx, col in enumerate(df.columns):
            max_length = max(
                df[col].astype(str).str.len().max(),
                len(col)
            ) + 2
            worksheet.column_dimensions[chr(65 + idx)].width = min(max_length, 50)

    return output.getvalue()


def get_unique_categories(instruments: List[UniverseInstrument]) -> List[str]:
    """Estrae lista di categorie uniche dagli strumenti."""
    categories = set()
    for inst in instruments:
        if inst.category_morningstar:
            categories.add(inst.category_morningstar)
    return sorted(categories)


def get_unique_sfdr_categories(instruments: List[UniverseInstrument]) -> List[str]:
    """Estrae lista di categorie SFDR uniche."""
    categories = set()
    for inst in instruments:
        if inst.category_sfdr:
            categories.add(inst.category_sfdr)
    return sorted(categories)


def apply_filters(
    instruments: List[UniverseInstrument],
    category_filter: Optional[str],
    sfdr_filter: Optional[str],
    min_perf: Optional[float],
    perf_period: str,
    max_ter: Optional[float]
) -> List[UniverseInstrument]:
    """Applica filtri alla lista di strumenti."""
    filtered = instruments

    # Filtro categoria Morningstar
    if category_filter and category_filter != "Tutte":
        filtered = [
            inst for inst in filtered
            if inst.category_morningstar and category_filter.lower() in inst.category_morningstar.lower()
        ]

    # Filtro categoria SFDR
    if sfdr_filter and sfdr_filter != "Tutte":
        filtered = [
            inst for inst in filtered
            if inst.category_sfdr and sfdr_filter.lower() in inst.category_sfdr.lower()
        ]

    # Filtro performance minima
    if min_perf is not None:
        min_perf_decimal = min_perf / 100  # Converti da percentuale a decimale
        filtered = filter_by_performance(filtered, perf_period, min_value=min_perf_decimal)

    # Filtro TER massimo
    if max_ter is not None:
        max_ter_decimal = max_ter / 100
        filtered = [
            inst for inst in filtered
            if inst.ter is None or inst.ter <= max_ter_decimal
        ]

    return filtered


# ============================================================================
# SIDEBAR - UPLOAD E FILTRI
# ============================================================================

with st.sidebar:
    st.title("📊 Selettore v3.1")
    st.divider()

    # =====================================
    # SEZIONE UPLOAD UNIVERSO
    # =====================================
    st.subheader("📁 Carica Universo Fondi")

    uploaded_file = st.file_uploader(
        "File Excel con dati completi",
        type=["xlsx", "xls"],
        help="File Excel con colonne: Nome, ISIN, Performance, Categoria Morningstar, TER, etc."
    )

    if uploaded_file is not None:
        # Carica solo se nuovo file o non ancora caricato
        if st.session_state.universe_filename != uploaded_file.name or not st.session_state.universe_loaded:
            result = load_universe(uploaded_file)

            if result:
                if result.valid_count > 0:
                    st.success(f"✅ {result.valid_count} fondi caricati")
                    if result.warnings:
                        with st.expander(f"⚠️ {len(result.warnings)} avvisi"):
                            for w in result.warnings[:10]:
                                st.warning(w)
                            if len(result.warnings) > 10:
                                st.info(f"...e altri {len(result.warnings) - 10} avvisi")
                else:
                    for err in result.errors:
                        st.error(err)
        else:
            # File gia' caricato
            st.success(f"✅ {st.session_state.universe_load_result.valid_count} fondi caricati")

    st.divider()

    # =====================================
    # FILTRI (solo se universo caricato)
    # =====================================
    category_filter = None
    sfdr_filter = None
    perf_period = "3y"
    min_perf = None
    max_ter = None
    sort_by = "3y"
    sort_ascending = False
    top_n = None

    if st.session_state.universe_loaded:
        st.subheader("🔧 Filtri")

        # Categorie disponibili
        available_categories = get_unique_categories(st.session_state.universe_instruments)
        available_sfdr = get_unique_sfdr_categories(st.session_state.universe_instruments)

        # Filtro categoria Morningstar
        if available_categories:
            category_filter = st.selectbox(
                "Categoria Morningstar",
                options=["Tutte"] + available_categories,
                index=0,
                help="Filtra per categoria Morningstar"
            )

        # Filtro SFDR
        if available_sfdr:
            sfdr_filter = st.selectbox(
                "Categoria SFDR",
                options=["Tutte"] + available_sfdr,
                index=0,
                help="Filtra per categoria SFDR (Art. 6, 8, 9)"
            )

        st.divider()

        # Performance
        st.subheader("📈 Performance")

        col1, col2 = st.columns(2)

        with col1:
            perf_period_label = st.selectbox(
                "Periodo",
                options=list(PERFORMANCE_PERIODS.keys()),
                index=4,  # default: 1 anno
                help="Periodo per filtro e ordinamento"
            )
            perf_period = PERFORMANCE_PERIODS[perf_period_label]

        with col2:
            min_perf = st.number_input(
                "Perf. min %",
                min_value=-100.0,
                max_value=500.0,
                value=0.0,
                step=5.0,
                help="Performance minima (in percentuale)"
            )
            if min_perf == 0.0:
                min_perf = None

        # TER massimo
        max_ter = st.number_input(
            "TER max %",
            min_value=0.0,
            max_value=10.0,
            value=3.0,
            step=0.1,
            help="Commissione massima annua"
        )
        if max_ter == 3.0:
            max_ter = None

        st.divider()

        # Ordinamento
        st.subheader("📊 Ordinamento")

        sort_by_label = st.selectbox(
            "Ordina per",
            options=list(PERFORMANCE_PERIODS.keys()),
            index=4,  # default: 1 anno
            help="Periodo per ordinamento"
        )
        sort_by = PERFORMANCE_PERIODS[sort_by_label]

        sort_ascending = st.checkbox(
            "Ordine crescente",
            value=False,
            help="Se attivo, mostra prima i peggiori"
        )

        top_n = st.number_input(
            "Mostra primi N",
            min_value=0,
            max_value=500,
            value=0,
            step=10,
            help="0 = mostra tutti"
        )
        if top_n == 0:
            top_n = None

        st.divider()

        # Pulsante applica filtri
        if st.button("🔎 APPLICA FILTRI", type="primary", use_container_width=True):
            # Applica filtri
            filtered = apply_filters(
                st.session_state.universe_instruments,
                category_filter if category_filter != "Tutte" else None,
                sfdr_filter if sfdr_filter != "Tutte" else None,
                min_perf,
                perf_period,
                max_ter
            )

            # Ordina
            filtered = rank_by_performance(filtered, sort_by, ascending=sort_ascending, top_n=top_n)

            st.session_state.filtered_instruments = filtered
            st.session_state.filter_applied = True

    # Info
    with st.expander("ℹ️ Informazioni"):
        st.markdown("""
        **Come usare:**
        1. Carica il file Excel con i dati dei fondi
        2. Applica filtri per categoria, performance, TER
        3. Visualizza i risultati ordinati
        4. Esporta in Excel

        **Formato file supportato:**
        - Nome, ISIN
        - Performance: YTD, 1m, 3m, 6m, 1a, 3a, 5a, 7a, 9a, 10a
        - Categoria Morningstar
        - Categoria SFDR
        - Commissioni (TER)
        - VaR 3m
        """)


# ============================================================================
# MAIN CONTENT
# ============================================================================

st.title("📊 Selettore Rendimenti Fondi/ETF")
st.caption(f"v{config.version} | Analisi e ranking fondi da file Excel")


# ============================================================================
# AREA RISULTATI
# ============================================================================

if not st.session_state.universe_loaded:
    st.info(
        "📁 **Carica il tuo file Excel** nella sidebar per iniziare.\n\n"
        "Il file deve contenere una colonna 'ISIN' e i dati di performance."
    )

else:
    # Statistiche universe
    total_instruments = len(st.session_state.universe_instruments)
    displayed_instruments = st.session_state.filtered_instruments
    displayed_count = len(displayed_instruments)

    if st.session_state.filter_applied:
        st.success(
            f"✅ Mostrati **{displayed_count}** fondi su {total_instruments} totali"
        )
    else:
        st.info(
            f"📊 **{total_instruments}** fondi caricati. Applica filtri per raffinare la ricerca."
        )
        displayed_instruments = st.session_state.universe_instruments

    # Metriche Summary
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Fondi Visualizzati",
            value=len(displayed_instruments)
        )

    with col2:
        # Calcola media performance sul periodo selezionato
        perfs = [
            inst.get_performance_by_period(sort_by if 'sort_by' in dir() else "1y")
            for inst in displayed_instruments
        ]
        valid_perfs = [p for p in perfs if p is not None]
        if valid_perfs:
            avg_perf = sum(valid_perfs) / len(valid_perfs) * 100
            st.metric(
                label="Media Performance",
                value=f"{avg_perf:.1f}%"
            )
        else:
            st.metric(label="Media Performance", value="N/A")

    with col3:
        # Migliore performance
        if valid_perfs:
            best_perf = max(valid_perfs) * 100
            st.metric(
                label="Migliore",
                value=f"{best_perf:.1f}%"
            )
        else:
            st.metric(label="Migliore", value="N/A")

    with col4:
        # Numero categorie
        cats = get_unique_categories(displayed_instruments)
        st.metric(
            label="Categorie",
            value=len(cats)
        )

    st.divider()

    # Tabella risultati
    st.subheader("📋 Fondi")

    df = universe_to_dataframe(displayed_instruments)

    if not df.empty:
        st.dataframe(
            df,
            hide_index=True,
            height=500,
            use_container_width=True
        )
    else:
        st.warning("Nessun fondo corrisponde ai filtri selezionati.")

    st.divider()

    # Download
    if displayed_instruments:
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"fondi_selezionati_{timestamp}.xlsx"

            excel_data = universe_to_excel(displayed_instruments)

            st.download_button(
                label="📥 SCARICA EXCEL",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                key="download_excel"
            )

            st.caption(f"File: {filename}")

    # Statistiche per categoria
    if displayed_instruments:
        st.divider()
        st.subheader("📊 Statistiche per Categoria")

        groups = group_by_category(displayed_instruments)

        # Calcola statistiche per ogni categoria
        stats_data = []
        for cat_name, cat_instruments in groups.items():
            perfs_1y = [
                inst.perf_1y for inst in cat_instruments
                if inst.perf_1y is not None
            ]
            perfs_3y = [
                inst.perf_3y for inst in cat_instruments
                if inst.perf_3y is not None
            ]

            stats_data.append({
                "Categoria": cat_name,
                "N. Fondi": len(cat_instruments),
                "Media 1a": f"{sum(perfs_1y) / len(perfs_1y) * 100:.1f}%" if perfs_1y else "N/A",
                "Media 3a": f"{sum(perfs_3y) / len(perfs_3y) * 100:.1f}%" if perfs_3y else "N/A",
                "Migliore 1a": f"{max(perfs_1y) * 100:.1f}%" if perfs_1y else "N/A",
                "Migliore 3a": f"{max(perfs_3y) * 100:.1f}%" if perfs_3y else "N/A",
            })

        stats_df = pd.DataFrame(stats_data)
        stats_df = stats_df.sort_values("N. Fondi", ascending=False)

        st.dataframe(
            stats_df,
            hide_index=True,
            use_container_width=True
        )


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption(
    f"📊 Selettore Rendimenti Fondi/ETF v{config.version} | "
    "Sviluppato da Boosha AI per Massimo Zaffanella | "
    f"© {datetime.now().year}"
)
