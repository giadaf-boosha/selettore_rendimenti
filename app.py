"""
Selettore Automatico Rendimenti Fondi/ETF v4.1

Web application Streamlit per l'analisi e il ranking di fondi comuni
a partire da file Excel con dati di performance completi.

Funzionalita' v4.1:
- Upload Universo Fondi da Excel (formato completo con performance)
- Selezione MULTIPLA categorie Morningstar
- Confronto con ETF benchmark (chi batte l'ETF?)
- Ranking per periodo di performance
- Export risultati in Excel
- Pre-caricamento database ETF (4000+ ETF) per ricerche istantanee

Autore: Boosha AI
Cliente: Massimo Zaffanella - Consulente Finanziario
Versione: 4.1.0
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
    rank_by_performance,
)
from core.etf_benchmark import get_etf_benchmark, get_etf_cache_status, preload_etf_list
from core.comparison_calculator import compare_universe_vs_etf
from utils.logger import setup_logging

# Setup logging
setup_logging(level=config.log_level, log_file=False)
logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURAZIONE PAGINA
# ============================================================================

st.set_page_config(
    page_title="Selettore Rendimenti Fondi/ETF v4.1",
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
        # Stato confronto ETF
        'comparison_report': None,
        'comparison_done': False,
        # Modalita' attiva
        'active_mode': 'esplora',
        # Stato database ETF (per pre-caricamento)
        'etf_db_ready': False,
        'etf_db_loaded_at': None,
        'etf_db_count': 0,
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
        st.session_state.comparison_report = None
        st.session_state.comparison_done = False

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


def comparison_to_excel(report) -> bytes:
    """Esporta risultati confronto in formato Excel."""
    data = []

    # Prima riga: ETF benchmark
    etf = report.etf_benchmark
    etf_perf = report.etf_performance
    data.append({
        "Nome": f"[BENCHMARK] {etf.name or etf.isin}",
        "ISIN": etf.isin,
        "Categoria": etf.category_morningstar or "",
        f"Perf. {report.period_label}": f"{etf_perf * 100:.2f}%" if etf_perf else "N/A",
        "Delta vs ETF": "BENCHMARK",
        "Status": "🎯 BENCHMARK"
    })

    # Risultati ordinati
    for r in report.get_sorted_results():
        row = {
            "Nome": r.instrument.name or r.instrument.isin,
            "ISIN": r.instrument.isin,
            "Categoria": r.instrument.category_morningstar or "",
            f"Perf. {report.period_label}": f"{r.fund_performance * 100:.2f}%" if r.fund_performance else "N/A",
            "Delta vs ETF": f"{r.delta * 100:+.2f}%" if r.delta else "N/A",
            "Status": r.status_emoji
        }
        data.append(row)

    df = pd.DataFrame(data)

    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Confronto ETF', index=False)

        # Auto-adjust column widths
        worksheet = writer.sheets['Confronto ETF']
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
    selected_categories: List[str],
    sfdr_filter: Optional[str]
) -> List[UniverseInstrument]:
    """
    Applica filtri alla lista di strumenti.

    Args:
        instruments: Lista strumenti da filtrare
        selected_categories: Lista categorie Morningstar selezionate (OR logic)
        sfdr_filter: Filtro categoria SFDR (singola selezione)

    Returns:
        Lista strumenti filtrati
    """
    filtered = instruments

    # Filtro categorie Morningstar (multiselect con logica OR)
    if selected_categories:
        filtered = [
            inst for inst in filtered
            if inst.category_morningstar and any(
                cat.lower() in inst.category_morningstar.lower()
                for cat in selected_categories
            )
        ]

    # Filtro categoria SFDR
    if sfdr_filter and sfdr_filter != "Tutte":
        filtered = [
            inst for inst in filtered
            if inst.category_sfdr and sfdr_filter.lower() in inst.category_sfdr.lower()
        ]

    return filtered


# ============================================================================
# SIDEBAR - UPLOAD E FILTRI
# ============================================================================

with st.sidebar:
    st.title("📊 Selettore v4.1")
    st.divider()

    # =====================================
    # SEZIONE UPLOAD UNIVERSO
    # =====================================
    st.subheader("📁 Carica Universo Fondi")

    uploaded_file = st.file_uploader(
        "File Excel con dati completi",
        type=["xlsx", "xls"],
        help="File Excel con colonne: Nome, ISIN, Performance, Categoria Morningstar, etc."
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
    # SEZIONE PRE-CARICAMENTO ETF BENCHMARK
    # =====================================
    st.subheader("📦 Prepara ETF Benchmark")

    cache_status = get_etf_cache_status()

    if cache_status['count'] > 0:
        st.success(
            f"✅ {cache_status['count']} ETF pronti\n"
            f"⏱️ Scade tra {cache_status['expires_in_minutes']} min"
        )
        with st.expander("📋 ETF in cache"):
            for isin in cache_status['isins']:
                st.text(f"• {isin}")
    else:
        st.info(
            "💡 Inserisci gli ISIN degli ETF benchmark\n"
            "che userai per i confronti"
        )

    # Input per lista ISIN
    etf_isins_input = st.text_area(
        "ISIN ETF da pre-caricare",
        placeholder="Inserisci gli ISIN (uno per riga o separati da virgola):\nIE00B5BMR087\nLU1900068328\nIE00B4L5Y983",
        height=100,
        help="Inserisci fino a 15 ISIN di ETF. Verranno scaricati e cachati per 24 ore."
    )

    # Pulsante per pre-caricare
    if st.button(
        "📥 PREPARA ETF",
        use_container_width=True,
        type="primary",
        help="Scarica i dati degli ETF inseriti (~2-3 sec per ETF). "
             "Le ricerche successive saranno istantanee per 24 ore."
    ):
        if not etf_isins_input.strip():
            st.warning("⚠️ Inserisci almeno un ISIN")
        else:
            # Parsa gli ISIN (supporta virgola, spazio, newline)
            import re
            isins = re.split(r'[,\s\n]+', etf_isins_input.strip())
            isins = [isin.strip().upper() for isin in isins if isin.strip()]

            if len(isins) > 15:
                st.warning("⚠️ Massimo 15 ISIN alla volta. Uso i primi 15.")
                isins = isins[:15]

            with st.spinner(f"⏳ Caricamento {len(isins)} ETF in corso..."):
                result = preload_etf_list(isins)

            # Mostra risultati
            if result['loaded']:
                st.success(f"✅ {len(result['loaded'])} ETF caricati con successo!")
                for item in result['loaded']:
                    cached_label = " (già in cache)" if item.get('cached') else ""
                    st.text(f"  ✓ {item['isin']}: {item['name']}{cached_label}")

            if result['failed']:
                st.warning(f"⚠️ {len(result['failed'])} ETF non trovati:")
                for item in result['failed']:
                    st.text(f"  ✗ {item['isin']}: {item['reason']}")

            if result['loaded']:
                st.rerun()

    st.divider()

    # =====================================
    # FILTRI (solo se universo caricato)
    # =====================================
    selected_categories = []
    sfdr_filter = None
    sort_by = "3y"
    sort_ascending = False
    top_n = None

    if st.session_state.universe_loaded:
        st.subheader("🔧 Filtri")

        # Categorie disponibili
        available_categories = get_unique_categories(st.session_state.universe_instruments)
        available_sfdr = get_unique_sfdr_categories(st.session_state.universe_instruments)

        # Filtro categorie Morningstar (MULTISELECT)
        if available_categories:
            selected_categories = st.multiselect(
                "Categorie Morningstar",
                options=available_categories,
                default=[],
                help="Seleziona una o piu' categorie (lascia vuoto per mostrare tutte)"
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

        # Ordinamento
        st.subheader("📊 Ordinamento")

        sort_by_label = st.selectbox(
            "Ordina per periodo",
            options=list(PERFORMANCE_PERIODS.keys()),
            index=4,  # default: 1 anno
            help="Periodo per ordinamento risultati"
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
                selected_categories,
                sfdr_filter if sfdr_filter != "Tutte" else None
            )

            # Ordina
            filtered = rank_by_performance(filtered, sort_by, ascending=sort_ascending, top_n=top_n)

            st.session_state.filtered_instruments = filtered
            st.session_state.filter_applied = True
            # Reset confronto quando cambiano i filtri
            st.session_state.comparison_report = None
            st.session_state.comparison_done = False

    # Info
    with st.expander("ℹ️ Informazioni"):
        st.markdown("""
        **Come usare:**
        1. Carica il file Excel con i dati dei fondi
        2. Seleziona una o piu' categorie Morningstar
        3. Inserisci l'ISIN di un ETF per confrontare
        4. Visualizza chi batte l'ETF
        5. Esporta i risultati in Excel

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
st.caption(f"v{config.version} | Analisi e confronto fondi vs ETF")


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

    # =========================================================================
    # SEZIONE CONFRONTO ETF
    # =========================================================================
    st.divider()
    st.subheader("🎯 Confronta con ETF Benchmark")

    st.markdown(
        "Inserisci l'ISIN di un ETF per vedere quali fondi lo battono "
        "nel periodo selezionato."
    )

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        etf_isin_input = st.text_input(
            "ISIN ETF Benchmark",
            placeholder="Es: IE00B5BMR087",
            help="Inserisci l'ISIN dell'ETF con cui confrontare i fondi"
        )

    with col2:
        comparison_period_label = st.selectbox(
            "Periodo Confronto",
            options=list(PERFORMANCE_PERIODS.keys()),
            index=5,  # default: 3 anni
            key="comparison_period",
            help="Periodo per il calcolo del delta"
        )
        comparison_period = PERFORMANCE_PERIODS[comparison_period_label]

    with col3:
        st.write("")  # Spacer
        st.write("")  # Spacer
        compare_button = st.button(
            "🔎 CONFRONTA",
            type="primary",
            use_container_width=True
        )

    if compare_button:
        if not etf_isin_input:
            st.warning("⚠️ Inserisci l'ISIN dell'ETF benchmark")
        else:
            # Verifica se l'ETF è nell'universo
            etf_in_universe = any(
                inst.isin.upper() == etf_isin_input.strip().upper()
                for inst in st.session_state.universe_instruments
            )

            # Se non è nell'universo, verifica se è in cache
            cache_status = get_etf_cache_status()
            etf_in_cache = etf_isin_input.strip().upper() in cache_status['isins']

            if not etf_in_universe and not etf_in_cache:
                st.info(
                    "ℹ️ ETF non in universo/cache. "
                    "Ricerca su fonti esterne (~5 sec)..."
                )

            # Recupera ETF
            spinner_msg = (
                "🔍 Ricerca dati ETF..."
                if etf_in_universe or etf_in_cache
                else "⏳ Ricerca ETF su fonti esterne..."
            )

            with st.spinner(spinner_msg):
                # Cerca nell'universo completo (non solo i filtrati)
                etf = get_etf_benchmark(
                    etf_isin_input,
                    st.session_state.universe_instruments
                )

            if etf is None:
                st.error(f"❌ ETF con ISIN '{etf_isin_input}' non trovato")
            else:
                # Esegui confronto sui fondi filtrati
                report = compare_universe_vs_etf(
                    displayed_instruments,
                    etf,
                    comparison_period,
                    comparison_period_label
                )
                st.session_state.comparison_report = report
                st.session_state.comparison_done = True

    # Mostra risultati confronto se disponibili
    if st.session_state.comparison_done and st.session_state.comparison_report:
        report = st.session_state.comparison_report

        st.divider()
        st.subheader("📋 Risultati Confronto")

        # Info ETF Benchmark
        etf = report.etf_benchmark
        etf_perf = report.etf_performance

        st.markdown(f"""
        **🎯 Benchmark:** {etf.name or etf.isin} ({etf.isin})
        **📊 Periodo:** {report.period_label}
        **📈 Performance ETF:** {f"{etf_perf * 100:.2f}%" if etf_perf else "N/A"}
        """)

        # Metriche confronto
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            if etf_perf:
                st.metric("Perf. ETF", f"{etf_perf * 100:.2f}%")
            else:
                st.metric("Perf. ETF", "N/A")

        with col2:
            st.metric(
                "✅ Battono ETF",
                report.funds_beating_etf,
                delta=f"{report.beat_percentage:.0f}%" if report.total_funds > 0 else None
            )

        with col3:
            st.metric(
                "❌ Non Battono",
                report.funds_not_beating_etf
            )

        with col4:
            if report.avg_delta:
                st.metric("Media Delta", f"{report.avg_delta * 100:+.2f}%")
            else:
                st.metric("Media Delta", "N/A")

        st.divider()

        # Tabella risultati
        comparison_data = []

        # Prima riga: ETF benchmark
        comparison_data.append({
            "Nome": f"🎯 {etf.name or etf.isin}",
            "ISIN": etf.isin,
            "Categoria": etf.category_morningstar or "-",
            f"Perf. {report.period_label}": f"{etf_perf * 100:.2f}%" if etf_perf else "N/A",
            "Delta vs ETF": "BENCHMARK",
            "Status": "🎯 BENCHMARK"
        })

        # Risultati ordinati
        for r in report.get_sorted_results():
            row = {
                "Nome": r.instrument.name or r.instrument.isin,
                "ISIN": r.instrument.isin,
                "Categoria": r.instrument.category_morningstar or "",
                f"Perf. {report.period_label}": f"{r.fund_performance * 100:.2f}%" if r.fund_performance else "N/A",
                "Delta vs ETF": f"{r.delta * 100:+.2f}%" if r.delta else "N/A",
                "Status": r.status_emoji
            }
            comparison_data.append(row)

        df_comparison = pd.DataFrame(comparison_data)

        # Mostra tabella con styling
        st.dataframe(
            df_comparison,
            hide_index=True,
            use_container_width=True,
            height=500
        )

        # Download risultati confronto
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            filename_comparison = f"confronto_etf_{etf.isin}_{timestamp}.xlsx"

            excel_data_comparison = comparison_to_excel(report)

            st.download_button(
                label="📥 SCARICA RISULTATI CONFRONTO",
                data=excel_data_comparison,
                file_name=filename_comparison,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                key="download_comparison"
            )

    # =========================================================================
    # TABELLA FONDI (se non in modalita' confronto)
    # =========================================================================
    if not st.session_state.comparison_done:
        st.divider()
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
    if displayed_instruments and not st.session_state.comparison_done:
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
