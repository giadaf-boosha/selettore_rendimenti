"""
Selettore Automatico Rendimenti Fondi/ETF v3.0

Web application Streamlit per la ricerca, il confronto e l'analisi
di fondi comuni e ETF su multiple piattaforme finanziarie.

Funzionalita' v3.0:
- Upload Universo Fondi da Excel
- Confronto Universo vs ETF per categoria
- Confronto ETF vs Universo
- Periodi estesi: 1m, 3m, 6m, YTD, 1-10 anni

Autore: Boosha AI
Cliente: Massimo Zaffanella - Consulente Finanziario
Versione: 3.0.0
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
    ComparisonReport,
)
from orchestrator.search_engine import SearchEngine
from orchestrator.comparison_engine import ComparisonEngine
from core.universe_loader import UniverseLoader
from exporters.excel_writer import ExcelWriter, instruments_to_dataframe
from utils.logger import setup_logging

# Setup logging
setup_logging(level=config.log_level, log_file=False)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURAZIONE PAGINA
# ============================================================================

st.set_page_config(
    page_title="Selettore Rendimenti Fondi/ETF v3.0",
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
        # Stato ricerca
        'search_in_progress': False,
        'search_completed': False,
        'search_error': None,
        'results': [],
        'results_df': None,
        'last_search_params': None,
        'total_results': 0,
        'progress_value': 0.0,
        'progress_message': '',
        # v3.0: Stato universo
        'universe_loaded': False,
        'universe_instruments': [],
        'universe_load_result': None,
        'universe_filename': None,
        # v3.0: Stato confronto
        'comparison_in_progress': False,
        'comparison_completed': False,
        'comparison_error': None,
        'comparison_report': None,
        # v3.0: Modalita' attiva
        'active_mode': 'ricerca',
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
def get_comparison_engine():
    """Restituisce istanza cached del comparison engine."""
    return ComparisonEngine()


@st.cache_resource
def get_universe_loader():
    """Restituisce istanza cached dell'universe loader."""
    return UniverseLoader()


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

        logger.info(f"Universe loaded: {result.valid_count} instruments")
        return result

    except Exception as e:
        logger.error(f"Universe load failed: {e}")
        st.session_state.universe_loaded = False
        st.session_state.universe_instruments = []
        return None


def execute_comparison_universe_vs_etf(category: str, category_type: str, periods: list):
    """Esegue confronto Universo vs ETF per categoria."""
    st.session_state.comparison_in_progress = True
    st.session_state.comparison_error = None

    try:
        engine = get_comparison_engine()
        report = engine.compare_universe_vs_etf_by_category(
            universe=st.session_state.universe_instruments,
            category=category,
            category_type=category_type,
            periods=periods,
            progress_callback=update_progress
        )

        st.session_state.comparison_report = report
        st.session_state.comparison_completed = True

        logger.info(f"Comparison completed: {len(report.results)} results")

    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        st.session_state.comparison_error = str(e)
        st.session_state.comparison_completed = False

    finally:
        st.session_state.comparison_in_progress = False


def execute_comparison_etf_vs_universe(etf_isin: str, periods: list):
    """Esegue confronto ETF vs Universo."""
    st.session_state.comparison_in_progress = True
    st.session_state.comparison_error = None

    try:
        engine = get_comparison_engine()
        report = engine.compare_etf_vs_universe(
            etf_isin=etf_isin,
            universe=st.session_state.universe_instruments,
            filter_by_category=True,
            periods=periods,
            progress_callback=update_progress
        )

        st.session_state.comparison_report = report
        st.session_state.comparison_completed = True

        logger.info(f"Comparison completed: {len(report.results)} results")

    except Exception as e:
        logger.error(f"Comparison failed: {e}")
        st.session_state.comparison_error = str(e)
        st.session_state.comparison_completed = False

    finally:
        st.session_state.comparison_in_progress = False


def get_excel_download(results: list) -> bytes:
    """Genera il file Excel per il download."""
    writer = get_excel_writer()
    buffer = writer.export(results)
    return buffer.getvalue()


def comparison_report_to_dataframe(report: ComparisonReport) -> pd.DataFrame:
    """Converte ComparisonReport in DataFrame per visualizzazione."""
    if not report or not report.results:
        return pd.DataFrame()

    data = []
    for result in report.results:
        row = {
            "Nome": result.instrument.name,
            "ISIN": result.instrument.isin,
            "Tipo": result.instrument.instrument_type.value,
            "Origine": result.origin.capitalize(),
            "Categoria": result.instrument.category_morningstar or result.instrument.category_assogestioni or "",
        }

        # Aggiungi performance
        for period_label, period_key in PERFORMANCE_PERIODS.items():
            perf = result.instrument.get_performance_by_period(period_key)
            col_name = f"Perf. {period_label}"
            row[col_name] = perf

        # Aggiungi delta (solo per strumenti universo)
        if result.origin == "universe":
            for period_label, period_key in PERFORMANCE_PERIODS.items():
                delta = result.get_delta_by_period(period_key)
                col_name = f"Delta {period_label}"
                row[col_name] = delta

        data.append(row)

    return pd.DataFrame(data)


# ============================================================================
# SIDEBAR - UPLOAD UNIVERSO E FILTRI
# ============================================================================

with st.sidebar:
    st.title("📊 Selettore v3.0")
    st.divider()

    # =====================================
    # SEZIONE UPLOAD UNIVERSO
    # =====================================
    st.subheader("📁 Universo Fondi")

    uploaded_file = st.file_uploader(
        "Carica file Excel",
        type=["xlsx", "xls"],
        help="File Excel con colonna ISIN dei tuoi fondi. Max 500 ISIN."
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

    # Mostra stato universo
    if st.session_state.universe_loaded:
        with st.expander("📋 Anteprima Universo"):
            preview_data = [
                {"ISIN": inst.isin, "Nome": inst.name or "-", "Cat.": inst.category or "-"}
                for inst in st.session_state.universe_instruments[:10]
            ]
            st.dataframe(pd.DataFrame(preview_data), hide_index=True, height=200)
            if len(st.session_state.universe_instruments) > 10:
                st.caption(f"...e altri {len(st.session_state.universe_instruments) - 10} fondi")

    st.divider()

    # =====================================
    # SELEZIONE MODALITA'
    # =====================================
    st.subheader("📌 Modalita'")

    modalita = st.radio(
        "Seleziona operazione",
        options=["🔍 Ricerca", "📊 Universo vs ETF", "📈 ETF vs Universo"],
        index=0,
        help="Ricerca: trova fondi/ETF. Confronto: paragona il tuo universo con ETF di mercato."
    )

    # Salva modalita' attiva
    st.session_state.active_mode = modalita

    st.divider()

    # =====================================
    # FILTRI (cambiano in base alla modalita')
    # =====================================
    st.subheader("🔧 Filtri")

    # Sistema di classificazione
    tipo_categoria = st.radio(
        "Sistema di classificazione",
        options=["Morningstar", "Assogestioni"],
        help="Scegli il sistema di categorizzazione"
    )

    # Categorie
    if tipo_categoria == "Morningstar":
        categorie_disponibili = MORNINGSTAR_CATEGORIES
    else:
        categorie_disponibili = ASSOGESTIONI_CATEGORIES

    if modalita in ["📊 Universo vs ETF", "📈 ETF vs Universo"]:
        # Per confronto: selezione singola categoria
        categoria_selezionata = st.selectbox(
            "Categoria",
            options=categorie_disponibili,
            index=0,
            help="Categoria per il confronto"
        )
    else:
        # Per ricerca: selezione multipla
        categorie_selezionate = st.multiselect(
            "Categorie",
            options=categorie_disponibili,
            default=[],
            help="Seleziona una o piu' categorie. Lascia vuoto per tutte."
        )

    # ETF ISIN input (solo per modalita' ETF vs Universo)
    etf_isin_input = ""
    if modalita == "📈 ETF vs Universo":
        etf_isin_input = st.text_input(
            "ISIN ETF",
            placeholder="es. IE00B4L5Y983",
            help="Inserisci l'ISIN dell'ETF da confrontare"
        )

    # Periodi per confronto
    if modalita in ["📊 Universo vs ETF", "📈 ETF vs Universo"]:
        periodi_selezionati = st.multiselect(
            "Periodi confronto",
            options=list(PERFORMANCE_PERIODS.keys()),
            default=["1 anno", "3 anni", "5 anni"],
            help="Periodi da includere nel confronto"
        )
    else:
        # Per ricerca standard
        col1, col2 = st.columns(2)

        with col1:
            periodo_label = st.selectbox(
                "Periodo",
                options=list(PERFORMANCE_PERIODS.keys()),
                index=4,  # default: 1 anno
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

    # Solo per modalita' ricerca: filtri aggiuntivi
    if modalita == "🔍 Ricerca":
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

    # =====================================
    # PULSANTE AZIONE
    # =====================================
    if modalita == "🔍 Ricerca":
        cerca_clicked = st.button(
            "🔎 CERCA",
            type="primary",
            key="search_button",
            use_container_width=True
        )
    elif modalita == "📊 Universo vs ETF":
        confronta_clicked = st.button(
            "📊 CONFRONTA",
            type="primary",
            key="compare_universe_button",
            use_container_width=True,
            disabled=not st.session_state.universe_loaded
        )
        if not st.session_state.universe_loaded:
            st.caption("⚠️ Carica prima l'universo fondi")
    else:  # ETF vs Universo
        confronta_etf_clicked = st.button(
            "📈 CONFRONTA",
            type="primary",
            key="compare_etf_button",
            use_container_width=True,
            disabled=not st.session_state.universe_loaded or not etf_isin_input
        )
        if not st.session_state.universe_loaded:
            st.caption("⚠️ Carica prima l'universo fondi")
        elif not etf_isin_input:
            st.caption("⚠️ Inserisci l'ISIN dell'ETF")

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
st.caption(f"v{config.version} | Ricerca e confronto automatizzato su JustETF, Morningstar e Investing.com")


# ============================================================================
# GESTIONE AZIONI - RICERCA
# ============================================================================

if modalita == "🔍 Ricerca" and 'cerca_clicked' in dir() and cerca_clicked:
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
# GESTIONE AZIONI - CONFRONTO UNIVERSO VS ETF
# ============================================================================

if modalita == "📊 Universo vs ETF" and 'confronta_clicked' in dir() and confronta_clicked:
    if st.session_state.universe_loaded:
        periods_keys = [PERFORMANCE_PERIODS[p] for p in periodi_selezionati]

        with st.spinner("Confronto in corso..."):
            progress_bar = st.progress(0)
            status_text = st.empty()

            execute_comparison_universe_vs_etf(
                category=categoria_selezionata,
                category_type=tipo_categoria.lower(),
                periods=periods_keys
            )

            progress_bar.progress(100)
            status_text.empty()


# ============================================================================
# GESTIONE AZIONI - CONFRONTO ETF VS UNIVERSO
# ============================================================================

if modalita == "📈 ETF vs Universo" and 'confronta_etf_clicked' in dir() and confronta_etf_clicked:
    if st.session_state.universe_loaded and etf_isin_input:
        periods_keys = [PERFORMANCE_PERIODS[p] for p in periodi_selezionati]

        with st.spinner("Confronto in corso..."):
            progress_bar = st.progress(0)
            status_text = st.empty()

            execute_comparison_etf_vs_universe(
                etf_isin=etf_isin_input.strip().upper(),
                periods=periods_keys
            )

            progress_bar.progress(100)
            status_text.empty()


# ============================================================================
# AREA RISULTATI - RICERCA
# ============================================================================

if modalita == "🔍 Ricerca":
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
            "- Selezionare piu' categorie\n"
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
                perf_col = f"Perf. {periodo_label.replace(' ', '')}" if 'periodo_label' in dir() else "Perf. 1a"
                if perf_col not in df.columns:
                    perf_col = "Perf. 1a"
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
            st.dataframe(
                st.session_state.results_df,
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
                    key="download_excel"
                )

                st.caption(f"File: {filename}")


# ============================================================================
# AREA RISULTATI - CONFRONTO
# ============================================================================

if modalita in ["📊 Universo vs ETF", "📈 ETF vs Universo"]:
    # Messaggio di stato
    if st.session_state.comparison_error:
        st.error(
            f"❌ **Errore durante il confronto:** {st.session_state.comparison_error}\n\n"
            "Verifica la connessione internet e riprova."
        )

    elif not st.session_state.comparison_completed and not st.session_state.comparison_in_progress:
        if not st.session_state.universe_loaded:
            st.info(
                "📁 **Carica il tuo Universo Fondi** nella sidebar per iniziare il confronto.\n\n"
                "Prepara un file Excel con una colonna 'ISIN' contenente i codici dei tuoi fondi."
            )
        else:
            st.info(
                f"✅ **{len(st.session_state.universe_instruments)} fondi caricati.**\n\n"
                f"Seleziona la categoria e clicca **CONFRONTA** per analizzare le performance."
            )

    elif st.session_state.comparison_completed and st.session_state.comparison_report:
        report = st.session_state.comparison_report

        if not report.results:
            st.warning("⚠️ **Nessun risultato** per il confronto selezionato.")
        else:
            st.success(
                f"✅ Confronto completato: **{report.total_instruments}** strumenti analizzati"
            )

            # Metriche Summary
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    label="Strumenti",
                    value=report.total_instruments
                )

            with col2:
                st.metric(
                    label="Outperformer",
                    value=report.outperformers_count,
                    delta=f"{report.outperformers_count / max(1, report.universe_count) * 100:.0f}%" if report.universe_count else None
                )

            with col3:
                avg_3y = report.avg_delta.get("3y")
                st.metric(
                    label="Media Delta 3a",
                    value=f"{avg_3y:+.2f}%" if avg_3y is not None else "N/A"
                )

            with col4:
                if report.best_performer:
                    delta_3y = report.best_performer.delta_3y
                    st.metric(
                        label="Best Performer",
                        value=f"{delta_3y:+.1f}%" if delta_3y is not None else "N/A"
                    )
                else:
                    st.metric(label="Best Performer", value="N/A")

            # Info benchmark
            if report.benchmark_etf:
                with st.expander("📌 ETF Benchmark"):
                    st.write(f"**Nome:** {report.benchmark_etf.name}")
                    st.write(f"**ISIN:** {report.benchmark_etf.isin}")
                    st.write(f"**Categoria:** {report.benchmark_etf.category_morningstar or report.benchmark_etf.category_assogestioni or 'N/A'}")

            st.divider()

            # Tabella confronto
            st.subheader("📋 Tabella Confronto")

            comparison_df = comparison_report_to_dataframe(report)

            if not comparison_df.empty:
                # Stile condizionale per i delta
                def style_delta(val):
                    if pd.isna(val):
                        return ""
                    if isinstance(val, (int, float)):
                        if val > 0.5:
                            return "background-color: rgba(0, 255, 0, 0.2)"
                        elif val < -0.5:
                            return "background-color: rgba(255, 0, 0, 0.2)"
                    return ""

                # Identifica colonne delta
                delta_cols = [col for col in comparison_df.columns if col.startswith("Delta")]

                # Mostra dataframe
                st.dataframe(
                    comparison_df,
                    hide_index=True,
                    height=500
                )

            st.divider()

            # Download confronto
            col1, col2, col3 = st.columns([1, 2, 1])

            with col2:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                filename = f"confronto_{timestamp}.xlsx"

                # Esporta solo gli strumenti aggregati (non ComparisonResult)
                instruments = [r.instrument for r in report.results]
                excel_data = get_excel_download(instruments)

                st.download_button(
                    label="📥 SCARICA CONFRONTO EXCEL",
                    data=excel_data,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    key="download_comparison_excel"
                )

                st.caption(f"File: {filename}")


# ============================================================================
# FOOTER
# ============================================================================

st.divider()
st.caption(
    f"📊 Selettore Rendimenti Fondi/ETF v{config.version} | "
    "Sviluppato da Boosha AI per Massimo Zaffanella | "
    f"© {datetime.now().year}"
)
