# Piano di Implementazione - Selettore Rendimenti v3.0

## Panoramica

Questo documento descrive il piano di implementazione per le nuove funzionalità del Selettore Rendimenti Fondi/ETF versione 3.0.

**Obiettivo principale:** Permettere il confronto tra i fondi del proprio "Universo" e gli ETF di mercato.

**Deployment target:** Streamlit Cloud

---

## Riepilogo Modifiche

### Nuovi File da Creare

| File | Descrizione | Priorità |
|------|-------------|----------|
| `core/universe_loader.py` | Parsing e validazione file Excel universo | Alta |
| `orchestrator/comparison_engine.py` | Logica confronto fondi vs ETF | Alta |
| `exporters/comparison_exporter.py` | Export Excel con formato confronto | Media |

### File da Modificare

| File | Modifiche | Priorità |
|------|-----------|----------|
| `config.py` | Aggiungere periodi 1m, 3m, 6m, 9y | Alta |
| `core/models.py` | Estendere PerformanceData, aggiungere UniverseInstrument | Alta |
| `app.py` | Upload universo, tab confronto, nuova UI | Alta |
| `scrapers/justetf_scraper.py` | Supporto nuovi periodi (se disponibili) | Media |
| `scrapers/morningstar_scraper.py` | Supporto nuovi periodi (se disponibili) | Media |
| `exporters/excel_writer.py` | Nuove colonne periodi | Media |

---

## Fase 1: Estensione Modelli e Configurazione

**Durata stimata:** 2 ore

### 1.1 Aggiornare `config.py`

```python
# Nuovi periodi da aggiungere
PERFORMANCE_PERIODS: Dict[str, str] = {
    "1 mese": "1m",      # NUOVO
    "3 mesi": "3m",      # NUOVO
    "6 mesi": "6m",      # NUOVO
    "YTD": "ytd",
    "1 anno": "1y",
    "3 anni": "3y",
    "5 anni": "5y",
    "7 anni": "7y",
    "9 anni": "9y",      # NUOVO
    "10 anni": "10y",
}

# Limiti per universo
UNIVERSE_MAX_ISINS = 500
UNIVERSE_ALLOWED_EXTENSIONS = [".xlsx", ".xls"]
```

### 1.2 Aggiornare `core/models.py`

**PerformanceData esteso:**
```python
@dataclass
class PerformanceData:
    return_1m: Optional[float] = None   # NUOVO
    return_3m: Optional[float] = None   # NUOVO
    return_6m: Optional[float] = None   # NUOVO
    ytd: Optional[float] = None
    return_1y: Optional[float] = None
    return_3y: Optional[float] = None
    return_5y: Optional[float] = None
    return_7y: Optional[float] = None
    return_9y: Optional[float] = None   # NUOVO
    return_10y: Optional[float] = None
```

**Nuovo dataclass UniverseInstrument:**
```python
@dataclass
class UniverseInstrument:
    """Strumento caricato dall'universo utente."""
    isin: str
    name: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    source_row: int = 0  # Riga nel file Excel originale
```

**Nuovo dataclass ComparisonResult:**
```python
@dataclass
class ComparisonResult:
    """Risultato confronto singolo strumento."""
    instrument: AggregatedInstrument
    origin: str  # "universe" o "market"
    benchmark_isin: Optional[str] = None
    delta_1m: Optional[float] = None
    delta_3m: Optional[float] = None
    delta_6m: Optional[float] = None
    delta_ytd: Optional[float] = None
    delta_1y: Optional[float] = None
    delta_3y: Optional[float] = None
    delta_5y: Optional[float] = None
    delta_7y: Optional[float] = None
    delta_9y: Optional[float] = None
    delta_10y: Optional[float] = None
```

### 1.3 Aggiornare `AggregatedInstrument`

Aggiungere campi per i nuovi periodi:
```python
perf_1m_eur: Optional[float] = None
perf_3m_eur: Optional[float] = None
perf_6m_eur: Optional[float] = None
perf_9y_eur: Optional[float] = None
```

---

## Fase 2: Universe Loader

**Durata stimata:** 3 ore

### 2.1 Creare `core/universe_loader.py`

**Funzionalità:**
- `load_universe(file_bytes: BytesIO) -> List[UniverseInstrument]`
- `validate_isin(isin: str) -> bool`
- `detect_isin_column(df: DataFrame) -> str`
- `parse_excel(file_bytes: BytesIO) -> DataFrame`

**Schema:**
```python
class UniverseLoader:
    """Carica e valida l'universo fondi da file Excel."""

    MAX_ISINS = 500
    ISIN_PATTERN = re.compile(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')

    def load(self, file: BytesIO) -> UniverseLoadResult:
        """
        Carica universo da file Excel.

        Returns:
            UniverseLoadResult con instruments validi e errori
        """
        pass

    def _detect_isin_column(self, df: DataFrame) -> Optional[str]:
        """Rileva automaticamente la colonna ISIN."""
        pass

    def _validate_isin(self, isin: str) -> bool:
        """Valida formato ISIN."""
        pass

@dataclass
class UniverseLoadResult:
    instruments: List[UniverseInstrument]
    errors: List[str]
    warnings: List[str]
    total_rows: int
    valid_count: int
    invalid_count: int
```

### 2.2 Gestione Errori

| Errore | Codice | Messaggio |
|--------|--------|-----------|
| Colonna ISIN non trovata | E001 | "Impossibile trovare colonna ISIN nel file" |
| ISIN invalido | W001 | "ISIN '{value}' non valido (riga {row})" |
| File vuoto | E002 | "Il file non contiene dati" |
| Limite superato | E003 | "Superato limite di {MAX_ISINS} ISIN" |
| Formato file errato | E004 | "Formato file non supportato" |

---

## Fase 3: Comparison Engine

**Durata stimata:** 4 ore

### 3.1 Creare `orchestrator/comparison_engine.py`

**Funzionalità principali:**

```python
class ComparisonEngine:
    """Motore di confronto fondi universo vs ETF."""

    def __init__(self, search_engine: SearchEngine):
        self.search_engine = search_engine
        self.merger = DataMerger()

    def compare_universe_vs_etf_by_category(
        self,
        universe: List[UniverseInstrument],
        category: str,
        category_type: str,  # "morningstar" o "assogestioni"
        periods: List[str],
        progress_callback: Optional[ProgressCallback] = None
    ) -> ComparisonReport:
        """
        Confronta fondi universo con ETF della stessa categoria.

        Flusso:
        1. Filtra universe per categoria
        2. Arricchisci fondi universe con dati da fonti
        3. Cerca ETF della stessa categoria
        4. Calcola delta performance
        5. Genera report confronto
        """
        pass

    def compare_etf_vs_universe(
        self,
        etf_isin: str,
        universe: List[UniverseInstrument],
        periods: List[str],
        progress_callback: Optional[ProgressCallback] = None
    ) -> ComparisonReport:
        """
        Confronta un ETF specifico con i fondi dell'universo.

        Flusso:
        1. Recupera dati ETF da fonti
        2. Identifica categoria ETF
        3. Filtra/mostra fondi universo (stessa categoria o tutti)
        4. Calcola delta performance
        5. Genera report confronto
        """
        pass

    def _calculate_deltas(
        self,
        instrument: AggregatedInstrument,
        benchmark: AggregatedInstrument,
        periods: List[str]
    ) -> Dict[str, Optional[float]]:
        """Calcola differenze di performance."""
        pass

    def _map_category(
        self,
        category: str,
        from_type: str,
        to_type: str
    ) -> Optional[str]:
        """Mappa categoria tra sistemi (Morningstar <-> Assogestioni)."""
        pass
```

### 3.2 ComparisonReport

```python
@dataclass
class ComparisonReport:
    """Report completo del confronto."""

    # Metadata
    comparison_type: str  # "universe_vs_etf" o "etf_vs_universe"
    category: Optional[str] = None
    benchmark_etf: Optional[AggregatedInstrument] = None
    periods_analyzed: List[str] = field(default_factory=list)
    generated_at: datetime = field(default_factory=datetime.now)

    # Risultati
    results: List[ComparisonResult] = field(default_factory=list)

    # Statistiche
    total_instruments: int = 0
    outperformers_count: int = 0
    underperformers_count: int = 0
    avg_delta: Dict[str, float] = field(default_factory=dict)
    best_performer: Optional[ComparisonResult] = None
    worst_performer: Optional[ComparisonResult] = None

    def to_dataframe(self) -> pd.DataFrame:
        """Converte in DataFrame per visualizzazione."""
        pass
```

### 3.3 Logica di Matching Categorie

Creare mapping tra categorie Assogestioni e Morningstar:

```python
CATEGORY_MAPPING = {
    # Assogestioni -> Morningstar
    "AZ. AMERICA": ["Azionari USA Large Cap Blend", "Azionari USA Large Cap Growth", "Azionari USA Large Cap Value"],
    "AZ. EUROPA": ["Azionari Europa Large Cap Blend", "Azionari Europa Large Cap Growth"],
    "AZ. INTERNAZIONALI": ["Azionari Globali Large Cap Blend", "Azionari Globali Large Cap Growth"],
    "AZ. PAESI EMERGENTI": ["Azionari Paesi Emergenti"],
    "AZ. ITALIA": ["Azionari Italia"],
    # ... completare
}
```

---

## Fase 4: UI Confronto

**Durata stimata:** 3 ore

### 4.1 Modifiche a `app.py`

**Nuova struttura:**

```python
# Sezione Upload Universo (sidebar)
with st.sidebar:
    st.subheader("📁 Universo Fondi")
    uploaded_file = st.file_uploader(
        "Carica file Excel",
        type=["xlsx", "xls"],
        help="File con colonna ISIN dei tuoi fondi"
    )

    if uploaded_file:
        # Carica e valida
        result = universe_loader.load(uploaded_file)
        st.session_state.universe = result.instruments

        # Mostra riepilogo
        st.success(f"✅ {result.valid_count} fondi caricati")
        if result.warnings:
            with st.expander("⚠️ Avvisi"):
                for w in result.warnings:
                    st.warning(w)

# Selezione modalità
modalita = st.radio(
    "Modalità",
    ["🔍 Ricerca", "📊 Confronto Universo vs ETF", "📈 Confronto ETF vs Universo"],
    horizontal=True
)

if modalita == "📊 Confronto Universo vs ETF":
    # UI per confronto categoria
    categoria = st.selectbox("Categoria", categorie_disponibili)
    periodi = st.multiselect("Periodi", list(PERFORMANCE_PERIODS.keys()), default=["1 anno", "3 anni", "5 anni"])

    if st.button("🔎 CONFRONTA"):
        # Esegui confronto
        report = comparison_engine.compare_universe_vs_etf_by_category(...)

        # Mostra risultati
        display_comparison_results(report)

elif modalita == "📈 Confronto ETF vs Universo":
    # UI per confronto ETF specifico
    etf_search = st.text_input("Cerca ETF (ISIN o nome)")

    # ... logica ricerca e confronto
```

### 4.2 Componenti Visualizzazione

**Tabella Confronto con Colori:**

```python
def display_comparison_table(report: ComparisonReport):
    """Mostra tabella confronto con indicatori visivi."""

    df = report.to_dataframe()

    # Configurazione colonne con colori
    column_config = {
        "Delta 1a": st.column_config.NumberColumn(
            "Δ 1a",
            format="%.2f%%",
            help="Differenza vs ETF benchmark"
        ),
        # ... altre colonne
    }

    # Styling con colori
    def color_delta(val):
        if val is None:
            return ""
        if val > 0.5:
            return "background-color: #90EE90"  # Verde chiaro
        elif val < -0.5:
            return "background-color: #FFB6C1"  # Rosso chiaro
        return ""

    styled_df = df.style.applymap(color_delta, subset=delta_columns)

    st.dataframe(styled_df, column_config=column_config, hide_index=True)
```

**Metriche Riepilogo:**

```python
def display_comparison_metrics(report: ComparisonReport):
    """Mostra metriche riepilogative."""

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Strumenti Confrontati",
            report.total_instruments
        )

    with col2:
        st.metric(
            "Outperformer",
            report.outperformers_count,
            delta=f"{report.outperformers_count/report.total_instruments*100:.0f}%"
        )

    with col3:
        st.metric(
            "Media Delta 3a",
            f"{report.avg_delta.get('3y', 0):.2f}%"
        )

    with col4:
        if report.best_performer:
            st.metric(
                "Best Performer",
                report.best_performer.instrument.name[:20] + "..."
            )
```

---

## Fase 5: Export Confronto Excel

**Durata stimata:** 2 ore

### 5.1 Creare `exporters/comparison_exporter.py`

```python
class ComparisonExporter:
    """Esporta report confronto in Excel formattato."""

    def export(self, report: ComparisonReport) -> BytesIO:
        """
        Genera file Excel con confronto.

        Fogli:
        1. "Confronto" - Tabella principale con delta
        2. "Riepilogo" - Statistiche e metriche
        3. "Benchmark" - Dettagli ETF benchmark
        """
        pass

    def _create_comparison_sheet(self, ws, report):
        """Crea foglio confronto con formattazione condizionale."""
        pass

    def _create_summary_sheet(self, ws, report):
        """Crea foglio riepilogo."""
        pass

    def _apply_conditional_formatting(self, ws, delta_columns):
        """Applica colori condizionali a delta."""
        # Verde per positivi, rosso per negativi
        pass
```

### 5.2 Formato Excel Output

**Foglio "Confronto":**

| Nome | ISIN | Origine | Cat. | 1m | 3m | 6m | YTD | 1a | 3a | 5a | 7a | 9a | 10a | Δ1a | Δ3a | Δ5a |
|------|------|---------|------|----|----|----|----|----|----|----|----|----|----|-----|-----|-----|
| Fondo A | LU... | Universo | Az. USA | 2.1% | 5.3% | ... | ... | 12.5% | 45.2% | ... | ... | ... | ... | +2.3% | +5.1% | -1.2% |
| ETF Benchmark | IE... | Mercato | Az. USA | 1.8% | 4.9% | ... | ... | 10.2% | 40.1% | ... | ... | ... | ... | - | - | - |

**Foglio "Riepilogo":**

| Metrica | Valore |
|---------|--------|
| Data confronto | 22/01/2026 |
| Categoria | Azionari USA |
| ETF Benchmark | iShares Core S&P 500 |
| Fondi confrontati | 12 |
| Outperformer (3a) | 5 (42%) |
| Media Delta 3a | +2.8% |
| Best Performer | Fondo XYZ (+8.5%) |
| Worst Performer | Fondo ABC (-3.2%) |

---

## Fase 6: Testing e Deploy

**Durata stimata:** 2 ore

### 6.1 Test Unitari

**File: `tests/unit/test_universe_loader.py`**
```python
def test_load_valid_excel():
    """Test caricamento file Excel valido."""
    pass

def test_validate_isin_format():
    """Test validazione formato ISIN."""
    pass

def test_detect_isin_column():
    """Test rilevamento automatico colonna ISIN."""
    pass

def test_handle_invalid_isins():
    """Test gestione ISIN invalidi."""
    pass

def test_max_isins_limit():
    """Test limite massimo ISIN."""
    pass
```

**File: `tests/unit/test_comparison_engine.py`**
```python
def test_compare_universe_vs_etf():
    """Test confronto universo vs ETF."""
    pass

def test_calculate_deltas():
    """Test calcolo delta performance."""
    pass

def test_category_mapping():
    """Test mapping categorie."""
    pass
```

### 6.2 Test Integrazione

**File: `tests/integration/test_comparison_flow.py`**
```python
def test_full_comparison_flow():
    """Test flusso completo upload -> confronto -> export."""
    pass
```

### 6.3 Checklist Deploy Streamlit Cloud

- [ ] Verificare `requirements.txt` aggiornato
- [ ] Testare in locale con `streamlit run app.py`
- [ ] Push su GitHub (branch main o production)
- [ ] Verificare deploy automatico su Streamlit Cloud
- [ ] Test funzionale su URL pubblico
- [ ] Verificare performance con 100+ ISIN

---

## Dipendenze tra Fasi

```
Fase 1 (Modelli) ─────┬────> Fase 2 (Universe Loader)
                      │
                      └────> Fase 3 (Comparison Engine) ────> Fase 4 (UI)
                                                                  │
                                                                  v
                                                        Fase 5 (Export)
                                                                  │
                                                                  v
                                                        Fase 6 (Deploy)
```

---

## Rischi e Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|-------------|---------|-------------|
| API fonti non supportano nuovi periodi | Media | Alto | Usare solo periodi disponibili, mostrare N/A |
| Performance lenta con 500 ISIN | Media | Medio | Cache aggressiva, progress bar, timeout |
| Mapping categorie incompleto | Alta | Medio | Permettere selezione manuale categoria ETF |
| File Excel formati diversi | Media | Basso | Rilevamento automatico + messaggi chiari |

---

## Stima Effort Totale

| Fase | Ore | Priorità |
|------|-----|----------|
| Fase 1: Modelli e Config | 2 | Alta |
| Fase 2: Universe Loader | 3 | Alta |
| Fase 3: Comparison Engine | 4 | Alta |
| Fase 4: UI Confronto | 3 | Alta |
| Fase 5: Export Excel | 2 | Media |
| Fase 6: Testing e Deploy | 2 | Alta |
| **TOTALE** | **16** | - |

---

*Piano generato il 22 gennaio 2026*
