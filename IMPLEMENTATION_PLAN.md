# Piano di Implementazione - Selettore Rendimenti v4.0

## Panoramica

Questo documento descrive il piano di implementazione per la versione 4.0 del Selettore Rendimenti Fondi/ETF, basato sul feedback di Massimo Zaffanella (owner del progetto) raccolto il 22 gennaio 2026.

**Obiettivo principale:** Permettere il confronto tra i fondi dell'universo e un ETF benchmark specifico per identificare chi lo batte.

**Deployment target:** Streamlit Cloud

---

## Riepilogo Feedback Ricevuti

| # | Minuto Transcript | Feedback | Azione Richiesta |
|---|-------------------|----------|------------------|
| 1 | - | Filtro potrebbe escludere risultati | Bug fix: verificare logica filtri |
| 2 | 45 | Confronto con ISIN ETF | Nuova funzionalita': inserire ISIN ETF e vedere chi lo batte |
| 3 | 48 | Selezione multipla categorie Morningstar | Cambiare da `selectbox` a `multiselect` |
| 4 | 50 | Non vuole min/max ma periodi temporali | Rimuovere filtri min/max performance |

---

## Riepilogo Modifiche

### Nuovi File da Creare

| File | Descrizione | Priorita' |
|------|-------------|-----------|
| `core/etf_benchmark.py` | Recupero dati ETF da universo o fonti esterne | Alta |
| `core/comparison_calculator.py` | Calcolo delta e classificazione fondi | Alta |

### File da Modificare

| File | Modifiche | Priorita' |
|------|-----------|-----------|
| `app.py` | Nuova sezione confronto ETF, multiselect categorie, rimozione filtri min/max | Alta |
| `core/universe_loader.py` | Verifica e fix logica filtri | Alta |
| `config.py` | Aggiornamento versione a 4.0 | Media |

---

## Fase 1: Bug Fix Filtri

**Durata stimata:** 1 ora

### 1.1 Analisi del Problema

Il feedback indica che i filtri potrebbero escludere risultati che dovrebbero essere inclusi. Verificare:

1. **Logica inclusiva vs esclusiva**: Assicurarsi che i filtri usino `>=` e `<=` invece di `>` e `<`
2. **Case sensitivity**: Verificare che il match delle categorie sia case-insensitive
3. **Valori null**: Verificare che i fondi senza categoria non vengano esclusi erroneamente
4. **Ranking**: Assicurarsi che la funzione `rank_by_performance` non perda elementi

### 1.2 Verifiche da Effettuare

```python
# In core/universe_loader.py

# 1. Verifica filter_by_performance usa >= e <= (non > e <)
def filter_by_performance(instruments, period, min_value=None, max_value=None):
    result = []
    for inst in instruments:
        perf = inst.get_performance_by_period(period)
        if perf is None:
            continue  # OK: esclude solo se non ha il dato
        if min_value is not None and perf < min_value:  # < e' corretto (esclude se sotto minimo)
            continue
        if max_value is not None and perf > max_value:  # > e' corretto (esclude se sopra massimo)
            continue
        result.append(inst)
    return result

# 2. Verifica match categorie in app.py (gia' usa .lower() per case-insensitivity)
# Ma verificare che il match sia inclusivo (substring match)
```

### 1.3 Test di Verifica

Creare test per verificare che i filtri funzionino correttamente:

- Test filtro categoria con case diversi
- Test filtro con valori al limite (boundary conditions)
- Test ranking mantiene tutti gli elementi

---

## Fase 2: Selezione Multipla Categorie Morningstar

**Durata stimata:** 1 ora

### 2.1 Modifica UI in `app.py`

**Codice attuale (da modificare):**
```python
# PRIMA (selectbox singolo)
category_filter = st.selectbox(
    "Categoria Morningstar",
    options=["Tutte"] + available_categories,
    index=0,
    help="Filtra per categoria Morningstar"
)
```

**Nuovo codice:**
```python
# DOPO (multiselect multiplo)
selected_categories = st.multiselect(
    "Categorie Morningstar",
    options=available_categories,
    default=[],
    help="Seleziona una o piu' categorie (lascia vuoto per mostrare tutte)"
)
```

### 2.2 Modifica Logica Filtro

**Codice attuale (da modificare):**
```python
# PRIMA
if category_filter and category_filter != "Tutte":
    filtered = [
        inst for inst in filtered
        if inst.category_morningstar and category_filter.lower() in inst.category_morningstar.lower()
    ]
```

**Nuovo codice:**
```python
# DOPO
if selected_categories:  # Se almeno una categoria selezionata
    filtered = [
        inst for inst in filtered
        if inst.category_morningstar and any(
            cat.lower() in inst.category_morningstar.lower()
            for cat in selected_categories
        )
    ]
# Se nessuna categoria selezionata, mostra tutti i fondi (nessun filtro)
```

---

## Fase 3: Rimozione Filtri Min/Max Performance

**Durata stimata:** 30 minuti

### 3.1 Elementi da Rimuovere in `app.py`

Rimuovere completamente:

1. Input "Perf. min %" (`st.number_input` con label "Perf. min %")
2. Input "TER max %" (`st.number_input` con label "TER max %")
3. Logica di filtro associata in `apply_filters()`
4. Parametri `min_perf`, `max_ter` dalla funzione

### 3.2 Elementi da Mantenere

- Selezione periodo per ordinamento (utile per visualizzare/ordinare)
- Ranking per performance (senza filtro soglia)

---

## Fase 4: Confronto con ETF Benchmark (Funzionalita' Principale)

**Durata stimata:** 4 ore

### 4.1 Creare `core/etf_benchmark.py`

```python
"""
ETF Benchmark - Recupero dati ETF per confronto.
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
        results = scraper.search_by_isin(isin)
        if results:
            return results[0]
    except Exception as e:
        logger.warning(f"Morningstar search failed for {isin}: {e}")

    # Prova JustETF
    try:
        from scrapers.justetf_scraper import JustETFScraper
        scraper = JustETFScraper()
        results = scraper.search_by_isin(isin)
        if results:
            return results[0]
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
        logger.info(f"ETF {isin} trovato nell'universo")
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
```

### 4.2 Creare `core/comparison_calculator.py`

```python
"""
Comparison Calculator - Calcola delta performance vs ETF benchmark.
"""
from typing import List, Optional, Dict
from dataclasses import dataclass, field
from core.models import UniverseInstrument
import logging

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Risultato confronto singolo fondo vs ETF."""
    instrument: UniverseInstrument
    etf_performance: Optional[float]
    fund_performance: Optional[float]
    delta: Optional[float]
    beats_etf: Optional[bool]  # True = batte, False = non batte, None = N/A

    @property
    def status(self) -> str:
        if self.beats_etf is True:
            return "BATTE"
        elif self.beats_etf is False:
            return "NON BATTE"
        else:
            return "N/A"


@dataclass
class ComparisonReport:
    """Report completo confronto universo vs ETF."""
    etf_benchmark: UniverseInstrument
    period: str
    period_label: str
    results: List[ComparisonResult] = field(default_factory=list)

    @property
    def total_funds(self) -> int:
        return len(self.results)

    @property
    def funds_beating_etf(self) -> int:
        return sum(1 for r in self.results if r.beats_etf is True)

    @property
    def funds_not_beating_etf(self) -> int:
        return sum(1 for r in self.results if r.beats_etf is False)

    @property
    def funds_no_data(self) -> int:
        return sum(1 for r in self.results if r.beats_etf is None)

    @property
    def etf_performance(self) -> Optional[float]:
        return self.etf_benchmark.get_performance_by_period(self.period)

    @property
    def avg_delta(self) -> Optional[float]:
        deltas = [r.delta for r in self.results if r.delta is not None]
        if deltas:
            return sum(deltas) / len(deltas)
        return None

    @property
    def best_performer(self) -> Optional[ComparisonResult]:
        valid = [r for r in self.results if r.delta is not None]
        if valid:
            return max(valid, key=lambda r: r.delta)
        return None

    @property
    def worst_performer(self) -> Optional[ComparisonResult]:
        valid = [r for r in self.results if r.delta is not None]
        if valid:
            return min(valid, key=lambda r: r.delta)
        return None

    def get_sorted_results(self, ascending: bool = False) -> List[ComparisonResult]:
        """Restituisce risultati ordinati per delta (default: migliori prima)."""
        # Separa risultati con e senza delta
        with_delta = [r for r in self.results if r.delta is not None]
        without_delta = [r for r in self.results if r.delta is None]

        # Ordina quelli con delta
        sorted_with_delta = sorted(
            with_delta,
            key=lambda r: r.delta,
            reverse=not ascending
        )

        # Risultati senza delta alla fine
        return sorted_with_delta + without_delta


def compare_universe_vs_etf(
    universe: List[UniverseInstrument],
    etf_benchmark: UniverseInstrument,
    period: str,
    period_label: str
) -> ComparisonReport:
    """
    Confronta tutti i fondi dell'universo con l'ETF benchmark.

    Args:
        universe: Lista fondi da confrontare
        etf_benchmark: ETF di riferimento
        period: Codice periodo (1m, 3m, 6m, ytd, 1y, 3y, 5y, 7y, 9y, 10y)
        period_label: Label periodo per display (es. "3 anni")

    Returns:
        ComparisonReport con tutti i risultati
    """
    report = ComparisonReport(
        etf_benchmark=etf_benchmark,
        period=period,
        period_label=period_label
    )

    etf_perf = etf_benchmark.get_performance_by_period(period)

    for fund in universe:
        # Escludi l'ETF stesso dal confronto
        if fund.isin == etf_benchmark.isin:
            continue

        fund_perf = fund.get_performance_by_period(period)

        # Calcola delta e status
        if etf_perf is not None and fund_perf is not None:
            delta = round(fund_perf - etf_perf, 4)  # In decimale
            beats_etf = delta > 0
        else:
            delta = None
            beats_etf = None

        result = ComparisonResult(
            instrument=fund,
            etf_performance=etf_perf,
            fund_performance=fund_perf,
            delta=delta,
            beats_etf=beats_etf
        )

        report.results.append(result)

    logger.info(
        f"Confronto completato: {report.funds_beating_etf} battono ETF, "
        f"{report.funds_not_beating_etf} non battono, {report.funds_no_data} N/A"
    )

    return report
```

### 4.3 Aggiornare `app.py` con Sezione Confronto

```python
# Nuova sezione nel main content

if st.session_state.universe_loaded:
    st.divider()
    st.subheader("🎯 Confronta con ETF Benchmark")

    col1, col2 = st.columns([2, 1])

    with col1:
        etf_isin = st.text_input(
            "ISIN ETF Benchmark",
            placeholder="Es: IE00B5BMR087",
            help="Inserisci l'ISIN dell'ETF con cui confrontare i fondi"
        )

    with col2:
        comparison_period_label = st.selectbox(
            "Periodo Confronto",
            options=list(PERFORMANCE_PERIODS.keys()),
            index=4,  # default: 1 anno
            help="Periodo per il calcolo del delta"
        )
        comparison_period = PERFORMANCE_PERIODS[comparison_period_label]

    if st.button("🔎 CONFRONTA CON ETF", type="primary", use_container_width=True):
        if not etf_isin:
            st.warning("Inserisci l'ISIN dell'ETF benchmark")
        else:
            # Recupera ETF
            from core.etf_benchmark import get_etf_benchmark
            from core.comparison_calculator import compare_universe_vs_etf

            with st.spinner("Ricerca dati ETF..."):
                etf = get_etf_benchmark(etf_isin, st.session_state.filtered_instruments)

            if etf is None:
                st.error(f"ETF con ISIN '{etf_isin}' non trovato")
            else:
                # Esegui confronto
                report = compare_universe_vs_etf(
                    st.session_state.filtered_instruments,
                    etf,
                    comparison_period,
                    comparison_period_label
                )

                # Mostra risultati
                st.success(f"Confronto completato con {etf.name or etf.isin}")

                # Metriche
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    etf_perf = report.etf_performance
                    if etf_perf:
                        st.metric("Perf. ETF", f"{etf_perf * 100:.2f}%")
                    else:
                        st.metric("Perf. ETF", "N/A")

                with col2:
                    st.metric(
                        "Battono ETF",
                        report.funds_beating_etf,
                        delta=f"{report.funds_beating_etf / max(report.total_funds, 1) * 100:.0f}%"
                    )

                with col3:
                    st.metric(
                        "Non Battono",
                        report.funds_not_beating_etf
                    )

                with col4:
                    if report.avg_delta:
                        st.metric("Media Delta", f"{report.avg_delta * 100:.2f}%")
                    else:
                        st.metric("Media Delta", "N/A")

                # Tabella risultati
                st.divider()
                st.subheader("📋 Risultati Confronto")

                # Converti in DataFrame per visualizzazione
                comparison_data = []
                for r in report.get_sorted_results():
                    row = {
                        "Nome": r.instrument.name or r.instrument.isin,
                        "ISIN": r.instrument.isin,
                        "Categoria": r.instrument.category_morningstar or "",
                        f"Perf. {comparison_period_label}": f"{r.fund_performance * 100:.2f}%" if r.fund_performance else "N/A",
                        "Delta vs ETF": f"{r.delta * 100:+.2f}%" if r.delta else "N/A",
                        "Status": r.status
                    }
                    comparison_data.append(row)

                df_comparison = pd.DataFrame(comparison_data)

                # Mostra tabella
                st.dataframe(
                    df_comparison,
                    hide_index=True,
                    use_container_width=True,
                    height=500
                )

                # Download
                # ... (logica export Excel)
```

---

## Fase 5: Testing

**Durata stimata:** 1 ora

### 5.1 Test Manuali da Eseguire

1. **Test selezione multipla categorie:**
   - Selezionare 0 categorie -> mostra tutti
   - Selezionare 1 categoria -> mostra solo quella
   - Selezionare 3 categorie -> mostra unione delle 3

2. **Test confronto ETF:**
   - ISIN valido presente nell'universo -> confronto immediato
   - ISIN valido non presente -> ricerca esterna (se implementata)
   - ISIN non valido -> messaggio errore
   - ISIN non trovato -> messaggio errore

3. **Test calcolo delta:**
   - Fondo con perf > ETF -> delta positivo, status "BATTE"
   - Fondo con perf < ETF -> delta negativo, status "NON BATTE"
   - Fondo senza perf -> delta N/A, status "N/A"

### 5.2 Test Automatici

File: `tests/test_comparison.py`

```python
def test_compare_universe_vs_etf():
    """Test confronto base."""
    pass

def test_delta_calculation():
    """Test calcolo delta."""
    pass

def test_multiselect_categories():
    """Test selezione multipla categorie."""
    pass
```

---

## Fase 6: Deploy

**Durata stimata:** 30 minuti

### 6.1 Aggiornare `config.py`

```python
version: str = "4.0.0"
```

### 6.2 Checklist Deploy

- [ ] Aggiornare `config.py` con versione 4.0.0
- [ ] Testare in locale con `streamlit run app.py`
- [ ] Commit e push su GitHub
- [ ] Verificare deploy automatico su Streamlit Cloud
- [ ] Test funzionale su URL pubblico
- [ ] Verificare confronto ETF con ISIN reale

---

## Dipendenze tra Fasi

```
Fase 1 (Bug Fix Filtri)
         │
         v
Fase 2 (Multiselect Categorie)
         │
         v
Fase 3 (Rimozione Filtri Min/Max)
         │
         v
Fase 4 (Confronto ETF) ─────────> Fase 5 (Testing)
                                        │
                                        v
                                  Fase 6 (Deploy)
```

---

## Stima Effort Totale

| Fase | Ore | Priorita' |
|------|-----|-----------|
| Fase 1: Bug Fix Filtri | 1 | Alta |
| Fase 2: Multiselect Categorie | 1 | Alta |
| Fase 3: Rimozione Filtri Min/Max | 0.5 | Alta |
| Fase 4: Confronto ETF | 4 | Alta |
| Fase 5: Testing | 1 | Alta |
| Fase 6: Deploy | 0.5 | Media |
| **TOTALE** | **8** | - |

---

## Rischi e Mitigazioni

| Rischio | Probabilita' | Impatto | Mitigazione |
|---------|--------------|---------|-------------|
| ETF non trovato su fonti esterne | Media | Alto | Prioritizzare ricerca nell'universo caricato |
| Performance lenta ricerca esterna | Media | Medio | Cache risultati, progress bar |
| Dati mancanti per alcuni periodi | Alta | Basso | Mostrare "N/A" invece di errore |
| Streamlit Cloud timeout | Bassa | Alto | Limitare ricerche esterne, usare cache |

---

## Note Tecniche

### Gestione ISIN ETF

L'approccio consigliato e':

1. **Prima**: Cercare l'ETF nell'universo caricato (veloce, dati consistenti)
2. **Poi**: Se non trovato, cercare su fonti esterne (Morningstar, JustETF)
3. **Fallback**: Mostrare errore se non trovato in nessuna fonte

### Colorazione Tabella

Streamlit supporta styling condizionale limitato. Opzioni:

1. **Colonna "Status"**: Testo colorato (piu' semplice)
2. **DataFrame Styling**: Usando `df.style.applymap()` (piu' complesso, compatibilita' limitata)
3. **Aggrid**: Componente avanzato (richiede dipendenza aggiuntiva)

Consigliato: Opzione 1 con emoji/icone per chiarezza visiva.

---

*Piano aggiornato il 22 gennaio 2026 sulla base del feedback di Massimo Zaffanella*
