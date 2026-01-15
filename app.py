"""
Selettore Automatico Rendimenti Fondi/ETF

Web application Streamlit per la ricerca e il confronto di fondi
comuni e ETF su multiple piattaforme finanziarie.

Autore: Boosha AI
Cliente: Massimo Zaffanella - Consulente Finanziario
Versione: 1.0.0
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import logging
import sys
from pathlib import Path

# Aggiungi la directory corrente al path per gli import
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    MORNINGSTAR_CATEGORIES,
    ASSOGESTIONI_CATEGORIES,
    CURRENCIES,
    PERFORMANCE_PERIODS,
    config,
)
from core.models import (
    SearchCriteria,
    InstrumentType,
    DistributionPolicy,
    AggregatedInstrument,
)
from orchestrator.search_engine import SearchEngine
from exporters.excel_writer import ExcelWriter, instruments_to_dataframe
from utils.logger import setup_logging

# Setup logging
setup_logging(level=config.log_level, log_file=False)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURAZIONE PAGINA
# ============================================================================

st.set_page_config(
    page_title="Selettore Rendimenti Fondi/ETF",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Selettore Automatico Rendimenti - v1.0.0 | Boosha AI"
    }
)


# ============================================================================
# INIZIALIZZAZIONE SESSION STATE
# ============================================================================

def init_session_state():
    """Inizializza le variabili di session state."""
    defaults = {
        'search_in_progress': False,
        'search_completed': False,
        'search_error': None,
        'results': [],
        'results_df': None,
        'last_search_params': None,
        'total_results': 0,
        'progress_value': 0.0,
        'progress_message': '',
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


init_session_state()


# ============================================================================
# FUNZIONI HELPER
# ============================================================================

@st.cache_resource
def get_search_engine():
    """Restituisce istanza cached del search engine."""
    return SearchEngine()


@st.cache_resource
def get_excel_writer():
    """Restituisce istanza cached dell'excel writer."""
    return ExcelWriter()


def update_progress(progress: float, message: str):
    """Callback per aggiornare la progress bar."""
    st.session_state.progress_value = progress
    st.session_state.progress_message = message


def execute_search(criteria: SearchCriteria):
    """Esegue la ricerca e aggiorna lo stato."""
    st.session_state.search_in_progress = True
    st.session_state.search_error = None
    st.session_state.last_search_params = criteria.to_dict()

    try:
        engine = get_search_engine()
        results = engine.search(criteria, progress_callback=update_progress)

        st.session_state.results = results
        st.session_state.results_df = instruments_to_dataframe(results)
        st.session_state.total_results = len(results)
        st.session_state.search_completed = True

        logger.info(f"Search completed: {len(results)} results")

    except Exception as e:
        logger.error(f"Search failed: {e}")
        st.session_state.search_error = str(e)
        st.session_state.search_completed = False
        st.session_state.results = []
        st.session_state.results_df = None

    finally:
        st.session_state.search_in_progress = False


def get_excel_download(results: list) -> bytes:
    """Genera il file Excel per il download."""
    writer = get_excel_writer()
    buffer = writer.export(results)
    return buffer.getvalue()


# ============================================================================
# SIDEBAR - FILTRI RICERCA
# ============================================================================

with st.sidebar:
    st.title("🔍 Filtri Ricerca")
    st.divider()

    # Tipo classificazione
    tipo_categoria = st.radio(
        "Sistema di classificazione",
        options=["Morningstar", "Assogestioni"],
        help="Scegli il sistema di categorizzazione dei fondi"
    )

    # Categorie (dinamico)
    if tipo_categoria == "Morningstar":
        categorie_disponibili = MORNINGSTAR_CATEGORIES
    else:
        categorie_disponibili = ASSOGESTIONI_CATEGORIES

    categorie_selezionate = st.multiselect(
        "Categorie",
        options=categorie_disponibili,
        default=[],
        help="Seleziona una o più categorie. Lascia vuoto per tutte."
    )

    st.divider()

    # Tipo strumento
    tipi_strumento = st.multiselect(
        "Tipo strumento",
        options=["ETF", "Fondi"],
        default=["ETF", "Fondi"],
        help="Filtra per tipo di strumento finanziario"
    )

    # Valuta
    valute = st.multiselect(
        "Valuta denominazione",
        options=CURRENCIES,
        default=["EUR"],
        help="Filtra per valuta dello strumento"
    )

    # Distribuzione
    distribuzione = st.radio(
        "Politica distribuzione",
        options=["Tutti", "Solo distribuzione", "Solo accumulo"],
        help="Filtra per tipologia cedole/dividendi"
    )

    st.divider()

    # Performance
    col1, col2 = st.columns(2)

    with col1:
        periodo_label = st.selectbox(
            "Periodo",
            options=list(PERFORMANCE_PERIODS.keys()),
            index=3,  # default: 5 anni
            help="Orizzonte temporale per il filtro performance"
        )
        periodo = PERFORMANCE_PERIODS[periodo_label]

    with col2:
        perf_min = st.number_input(
            "Perf. min %",
            min_value=-100.0,
            max_value=500.0,
            value=0.0,
            step=5.0,
            help="Performance minima richiesta"
        )

    st.divider()

    # Pulsante ricerca
    cerca_clicked = st.button(
        "🔎 CERCA",
        type="primary",
        use_container_width=True
    )

    # Info fonti
    with st.expander("ℹ️ Informazioni sulle fonti"):
        st.markdown("""
        **Fonti dati:**
        - 🟢 **JustETF**: ETF quotati in Europa
        - 🟢 **Morningstar**: ETF e Fondi globali
        - 🟡 **Investing.com**: Dati limitati (via investiny)

        I dati vengono aggregati tramite codice ISIN.
        """)


# ============================================================================
# MAIN CONTENT
# ============================================================================

st.title("📊 Selettore Rendimenti Fondi/ETF")
st.caption("Ricerca automatizzata su JustETF, Morningstar e Investing.com")

# Gestione click pulsante CERCA
if cerca_clicked:
    # Costruisci criteri
    instrument_types = []
    if "ETF" in tipi_strumento:
        instrument_types.append(InstrumentType.ETF)
    if "Fondi" in tipi_strumento:
        instrument_types.append(InstrumentType.FUND)

    distribution_filter = None
    if distribuzione == "Solo distribuzione":
        distribution_filter = DistributionPolicy.DISTRIBUTING
    elif distribuzione == "Solo accumulo":
        distribution_filter = DistributionPolicy.ACCUMULATING

    criteria = SearchCriteria(
        categories_morningstar=categorie_selezionate if tipo_categoria == "Morningstar" else [],
        categories_assogestioni=categorie_selezionate if tipo_categoria == "Assogestioni" else [],
        currencies=valute if valute else ["EUR"],
        distribution_filter=distribution_filter,
        min_performance=perf_min if perf_min != 0 else None,
        performance_period=periodo,
        instrument_types=instrument_types if instrument_types else [InstrumentType.ETF, InstrumentType.FUND],
    )

    # Mostra progress bar durante la ricerca
    with st.spinner("Ricerca in corso..."):
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Esegui ricerca
        execute_search(criteria)

        # Aggiorna UI
        progress_bar.progress(100)
        status_text.empty()


# ============================================================================
# AREA RISULTATI
# ============================================================================

# Messaggio di stato
if st.session_state.search_error:
    st.error(
        f"❌ **Errore durante la ricerca:** {st.session_state.search_error}\n\n"
        "Verifica la connessione internet e riprova."
    )

elif not st.session_state.search_completed and not st.session_state.search_in_progress:
    st.info(
        "👋 **Benvenuto!** Seleziona i criteri di ricerca nella sidebar "
        "e clicca **CERCA** per trovare i migliori fondi ed ETF."
    )

elif st.session_state.search_completed and st.session_state.total_results == 0:
    st.warning(
        "⚠️ **Nessun risultato trovato** con i criteri selezionati.\n\n"
        "Prova a:\n"
        "- Abbassare la soglia di performance minima\n"
        "- Selezionare più categorie\n"
        "- Includere altre valute"
    )

elif st.session_state.search_completed and st.session_state.total_results > 0:
    st.success(
        f"✅ Trovati **{st.session_state.total_results}** strumenti "
        f"corrispondenti ai criteri di ricerca."
    )

    # Metriche Summary
    if st.session_state.results_df is not None:
        df = st.session_state.results_df

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="Strumenti Trovati",
                value=len(df)
            )

        with col2:
            perf_col = f"Perf. {periodo_label.replace(' ', '')}" if 'periodo_label' in dir() else "Perf. 5a"
            if perf_col not in df.columns:
                perf_col = "Perf. 5a"
            if perf_col in df.columns and not df[perf_col].isna().all():
                avg_perf = df[perf_col].mean()
                st.metric(
                    label=f"Media {perf_col}",
                    value=f"{avg_perf:.1f}%" if pd.notna(avg_perf) else "N/A"
                )
            else:
                st.metric(label="Media Perf.", value="N/A")

        with col3:
            if perf_col in df.columns and not df[perf_col].isna().all():
                best_perf = df[perf_col].max()
                st.metric(
                    label=f"Migliore {perf_col}",
                    value=f"{best_perf:.1f}%" if pd.notna(best_perf) else "N/A"
                )
            else:
                st.metric(label="Migliore Perf.", value="N/A")

        with col4:
            if "Fonti" in df.columns:
                # Conta fonti uniche
                all_sources = set()
                for sources_str in df["Fonti"].dropna():
                    for s in str(sources_str).split(", "):
                        if s.strip():
                            all_sources.add(s.strip())
                st.metric(label="Fonti Dati", value=len(all_sources))
            else:
                st.metric(label="Fonti Dati", value="N/A")

    st.divider()

    # Tabella risultati
    st.subheader("📋 Risultati")

    if st.session_state.results_df is not None:
        # Configurazione colonne per st.dataframe
        column_config = {
            "Nome": st.column_config.TextColumn(
                "Nome Strumento",
                width="large",
                help="Nome completo del fondo o ETF"
            ),
            "ISIN": st.column_config.TextColumn(
                "ISIN",
                width="small",
                help="Codice identificativo univoco"
            ),
            "Tipo": st.column_config.TextColumn(
                "Tipo",
                width="small"
            ),
            "Valuta": st.column_config.TextColumn(
                "Valuta",
                width="small"
            ),
            "Perf. YTD": st.column_config.NumberColumn(
                "YTD %",
                format="%.2f%%",
                help="Performance Year-To-Date"
            ),
            "Perf. 1a": st.column_config.NumberColumn(
                "1 Anno %",
                format="%.2f%%"
            ),
            "Perf. 3a": st.column_config.NumberColumn(
                "3 Anni %",
                format="%.2f%%"
            ),
            "Perf. 5a": st.column_config.NumberColumn(
                "5 Anni %",
                format="%.2f%%"
            ),
            "Perf. 7a": st.column_config.NumberColumn(
                "7 Anni %",
                format="%.2f%%"
            ),
            "Perf. 10a": st.column_config.NumberColumn(
                "10 Anni %",
                format="%.2f%%"
            ),
        }

        st.dataframe(
            st.session_state.results_df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
            height=500
        )

    st.divider()

    # Download Button
    if st.session_state.results:
        col1, col2, col3 = st.columns([1, 2, 1])

        with col2:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename = f"rendimenti_fondi_{timestamp}.xlsx"

            excel_data = get_excel_download(st.session_state.results)

            st.download_button(
                label="📥 SCARICA EXCEL",
                data=excel_data,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True
            )

            st.caption(f"File: {filename}")


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption(
    "📊 Selettore Rendimenti Fondi/ETF v1.0.0 | "
    "Sviluppato da Boosha AI per Massimo Zaffanella | "
    f"© {datetime.now().year}"
)
