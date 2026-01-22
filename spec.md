# DOCUMENTO DI SPECIFICHE
## Selettore Automatico Rendimenti Fondi/ETF - v4.0

---

| | |
|---|---|
| **Cliente** | Massimo Zaffanella - Consulente Finanziario |
| **Progetto** | AI Acceleration Program - Automazione Back-Office |
| **Data** | 22 gennaio 2026 |
| **Versione** | 4.0 |
| **Deployment** | Streamlit Cloud (https://streamlit.io/) |

---

## 1. Contesto e Obiettivo

### 1.1 Situazione Attuale

Massimo Zaffanella, consulente finanziario, ha a disposizione un **universo di circa 3000+ fondi** che puo' proporre ai propri clienti. La sfida principale e' identificare rapidamente quali fondi hanno performance migliori rispetto agli ETF equivalenti di mercato.

**Problema chiave (dal transcript):**
> "Me lo fa su tutti i fondi. Ci sono 12.000 fondi. A me sapere che 5.000 degli altri fondi che io non posso fare hanno fatto meglio, non interessa. Interessa farlo sull'universo di investimento che io ho a disposizione."

La versione 3.1 ha implementato il caricamento dell'universo da Excel, ma manca la funzionalita' principale: **il confronto diretto con un ETF benchmark per identificare chi lo batte**.

### 1.2 Obiettivo del Progetto (v4.0)

Estendere l'applicazione per permettere a Massimo di:

1. **Caricare il proprio "Universo Fondi"** tramite file Excel (gia' implementato in v3.1)
2. **Selezionare MULTIPLE categorie Morningstar** per filtrare l'universo
3. **Inserire l'ISIN di un ETF specifico** e confrontarlo con i fondi dell'universo
4. **Visualizzare chi batte l'ETF** con evidenziazione chiara dei risultati
5. **Esportare i risultati** in formato Excel

### 1.3 Principio Guida

> "Io vado a cercare l'ISIN dell'ETF e gli dico 'Confrontamene con quelli qua, chi l'ha battuto?' e lui mi restituisce un nuovo file o una nuova tabella con evidenziato chi sono quelli che l'hanno battuto."
> — Massimo Zaffanella (Transcript min. 45)

---

## 2. Requisiti Funzionali

### 2.1 Funzionalita' Esistenti (v3.1 - Mantenute)

#### RF-01: Upload Universo Fondi
- Caricamento file Excel con dati completi (Nome, ISIN, Performance, Categorie, TER)
- Validazione ISIN
- Supporto fino a 5000 strumenti
- Parsing automatico colonne con mapping flessibile

#### RF-02: Visualizzazione Dati
- Tabella interattiva con tutti i dati caricati
- Formattazione performance in percentuale
- Export Excel dei risultati

---

### 2.2 Nuove Funzionalita' (v4.0)

#### RF-03: Selezione Multipla Categorie Morningstar [NUOVO]

**Requisito dal transcript (min. 48):**
> "Morningstar e' molto specialistico, quindi lui l'azionario americano lo divide in tanti sottosettori... Io vorrei poter selezionare piu' di uno, quindi dammi il large value, growth e blend tutti e tre."

| Elemento | Descrizione |
|----------|-------------|
| **Componente UI** | `st.multiselect` invece di `st.selectbox` |
| **Comportamento** | Selezione di 1 o piu' categorie contemporaneamente |
| **Logica filtro** | OR tra le categorie selezionate (un fondo e' incluso se appartiene ad ALMENO UNA delle categorie selezionate) |
| **Default** | Nessuna categoria selezionata = mostra tutti i fondi |

**Esempio d'uso:**
- Utente seleziona: "Azionari USA Large Cap Blend", "Azionari USA Large Cap Growth", "Azionari USA Large Cap Value"
- Sistema mostra tutti i fondi che appartengono a una qualsiasi di queste 3 categorie

#### RF-04: Confronto con ETF Specifico [NUOVO - FUNZIONALITA' PRINCIPALE]

**Requisito dal transcript (min. 45):**
> "Bisognerebbe aggiungere proprio una caratteristica del tipo confrontalo con quell'ETF. Io vado a cercare l'ISIN dell'ETF, che e' la cosa piu' semplice. Vado a cercare l'ISIN dell'ETF e gli dico 'Confrontamene con quelli qua, chi l'ha battuto?'"

**Flusso operativo:**

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. CARICA UNIVERSO                                              │
│    └─> File Excel con 3000+ fondi                               │
├─────────────────────────────────────────────────────────────────┤
│ 2. FILTRA PER CATEGORIA (opzionale)                             │
│    └─> Seleziona 1+ categorie Morningstar                       │
├─────────────────────────────────────────────────────────────────┤
│ 3. INSERISCI ISIN ETF BENCHMARK                                 │
│    └─> Es: IE00B5BMR087 (iShares Core S&P 500)                  │
├─────────────────────────────────────────────────────────────────┤
│ 4. SELEZIONA PERIODO DI CONFRONTO                               │
│    └─> Es: 3 anni                                               │
├─────────────────────────────────────────────────────────────────┤
│ 5. CLICCA "CONFRONTA"                                           │
│    └─> Sistema cerca performance ETF su fonti esterne           │
├─────────────────────────────────────────────────────────────────┤
│ 6. VISUALIZZA RISULTATI                                         │
│    └─> Tabella con:                                             │
│        - ETF benchmark (in evidenza)                            │
│        - Fondi che BATTONO l'ETF (verde, in alto)               │
│        - Fondi che NON battono l'ETF (rosso, in basso)          │
│        - Delta performance per ogni fondo                       │
├─────────────────────────────────────────────────────────────────┤
│ 7. ESPORTA EXCEL                                                │
│    └─> File con risultati confronto                             │
└─────────────────────────────────────────────────────────────────┘
```

**Componenti UI:**

| Componente | Tipo Streamlit | Descrizione |
|------------|----------------|-------------|
| Input ISIN ETF | `st.text_input` | Campo per inserire ISIN ETF benchmark |
| Selezione Periodo | `st.selectbox` | Periodo per il confronto (1m, 3m, 6m, YTD, 1a, 3a, 5a, 7a, 9a, 10a) |
| Pulsante Confronta | `st.button` | Avvia il confronto |
| Tabella Risultati | `st.dataframe` | Con colorazione condizionale |

**Logica di confronto:**

```
Per ogni fondo nell'universo filtrato:
    perf_fondo = performance del fondo nel periodo selezionato
    perf_etf = performance dell'ETF nel periodo selezionato

    delta = perf_fondo - perf_etf

    Se delta > 0:
        fondo BATTE l'ETF (evidenziare in verde)
    Se delta < 0:
        fondo NON batte l'ETF (evidenziare in rosso)
    Se delta == 0:
        performance PARI (evidenziare in grigio)
```

#### RF-05: Rimozione Filtri Min/Max Performance [MODIFICA]

**Requisito dal transcript (min. 50):**
> "A me servirebbe le varie performance che ci sono nel file Excel, ovvero non tanto la performance minima e massima, ma la performance che ha fatto in un arco temporale. Quindi il minimo e il massimo non mi interessa."

**Cambio richiesto:**
- RIMUOVERE: Input "Perf. min %" e "TER max %"
- MANTENERE: Selezione periodo temporale per visualizzazione/ordinamento
- AGGIUNGERE: La logica di filtro "chi batte l'ETF" sostituisce i filtri min/max

#### RF-06: Fix Potenziale Bug Filtri [BUG FIX]

**Segnalazione (punto 1 dei feedback):**
> "Forse il filtro non viene applicato potrebbe escludere alcuni risultati"

**Azione richiesta:**
- Verificare che i filtri usino logica inclusiva (>=, <=) non esclusiva (>, <)
- Verificare che il match delle categorie sia case-insensitive
- Verificare che i fondi senza categoria non vengano esclusi erroneamente
- Assicurarsi che il ranking non perda elementi

---

### 2.3 Interfaccia Utente (v4.0)

#### RF-07: Layout Aggiornato

```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 Selettore Rendimenti Fondi/ETF v4.0                          │
├─────────────────┬───────────────────────────────────────────────┤
│                 │                                               │
│  SIDEBAR        │   MAIN CONTENT                                │
│                 │                                               │
│  ┌───────────┐  │   ┌─────────────────────────────────────────┐ │
│  │📁 CARICA  │  │   │ 📊 Universo Caricato                    │ │
│  │ UNIVERSO  │  │   │ ✅ 3432 fondi | 45 categorie           │ │
│  └───────────┘  │   └─────────────────────────────────────────┘ │
│                 │                                               │
│  ──────────────  │   ┌─────────────────────────────────────────┐ │
│                 │   │ 🔍 CONFRONTA CON ETF                    │ │
│  🏷️ CATEGORIE   │   │ ──────────────────────────────────────── │ │
│  [Multiselect]  │   │                                         │ │
│  ☑ Large Blend  │   │ ISIN ETF: [________________]            │ │
│  ☑ Large Growth │   │                                         │ │
│  ☑ Large Value  │   │ Periodo:  [3 anni ▼]                    │ │
│  ☐ Mid Cap      │   │                                         │ │
│  ☐ Small Cap    │   │ [🔎 CONFRONTA]                          │ │
│                 │   │                                         │ │
│  ──────────────  │   └─────────────────────────────────────────┘ │
│                 │                                               │
│  📊 PERIODO     │   ┌─────────────────────────────────────────┐ │
│  [3 anni ▼]     │   │ 📋 RISULTATI CONFRONTO                  │ │
│                 │   │ ──────────────────────────────────────── │ │
│  ──────────────  │   │ 🎯 Benchmark: iShares S&P 500          │ │
│                 │   │    Perf. 3a: +45.2%                     │ │
│  [🔎 FILTRA]    │   │                                         │ │
│                 │   │ ✅ 127 fondi BATTONO l'ETF              │ │
│                 │   │ ❌ 215 fondi NON battono l'ETF          │ │
│                 │   │                                         │ │
│                 │   │ ┌────┬────┬────┬────┬────────────────┐  │ │
│                 │   │ │Nome│ISIN│Cat │3a  │Delta vs ETF    │  │ │
│                 │   │ ├────┼────┼────┼────┼────────────────┤  │ │
│                 │   │ │... │... │... │52% │ ✅ +6.8%       │  │ │
│                 │   │ │... │... │... │48% │ ✅ +2.8%       │  │ │
│                 │   │ │ETF │IE..│-   │45% │ BENCHMARK      │  │ │
│                 │   │ │... │... │... │42% │ ❌ -3.2%       │  │ │
│                 │   │ └────┴────┴────┴────┴────────────────┘  │ │
│                 │   │                                         │ │
│                 │   │ [📥 SCARICA EXCEL]                      │ │
│                 │   └─────────────────────────────────────────┘ │
└─────────────────┴───────────────────────────────────────────────┘
```

#### RF-08: Componenti UI Nuovi

| Componente | Tipo Streamlit | Descrizione |
|------------|----------------|-------------|
| Multiselect Categorie | `st.multiselect` | Selezione multipla categorie Morningstar |
| Input ISIN ETF | `st.text_input` | Campo per ISIN ETF benchmark |
| Selezione Periodo | `st.selectbox` | Periodo per confronto |
| Pulsante Confronta | `st.button` | Avvia confronto con ETF |
| Metriche Confronto | `st.metric` | Contatori fondi che battono/non battono |
| Tabella Colorata | `st.dataframe` | Con styling condizionale verde/rosso |

---

## 3. Requisiti Tecnici

### 3.1 Architettura (v4.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Streamlit)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Upload    │  │ Multiselect │  │   Confronto ETF         │  │
│  │  Universo   │  │  Categorie  │  │   + Visualizzazione     │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    BUSINESS LOGIC                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Universe   │  │  Category   │  │   ETF Comparison        │  │
│  │   Loader    │  │   Filter    │  │   Engine (NUOVO)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    DATA LAYER                                    │
│  ┌───────────┐  ┌────────────┐  ┌───────────────────────────┐  │
│  │  Excel    │  │ Morningstar│  │  JustETF (per dati ETF)   │  │
│  │  Parser   │  │  Scraper   │  │                           │  │
│  └───────────┘  └────────────┘  └───────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Nuovi Moduli da Implementare

| Modulo | Path | Responsabilita' |
|--------|------|-----------------|
| `etf_benchmark.py` | `core/` | Recupero dati ETF da fonti esterne |
| `comparison_calculator.py` | `core/` | Calcolo delta e classificazione fondi |

### 3.3 Modifiche ai Moduli Esistenti

| Modulo | Modifiche |
|--------|-----------|
| `app.py` | Nuova sezione confronto ETF, multiselect categorie, rimozione filtri min/max |
| `universe_loader.py` | Verifica e fix logica filtri |
| `config.py` | Aggiornamento versione a 4.0 |

### 3.4 Recupero Dati ETF Benchmark

Per recuperare le performance dell'ETF inserito dall'utente:

**Opzione 1 (Consigliata): Ricerca nell'universo stesso**
- Se l'ETF e' gia' presente nel file Excel caricato, usa quei dati
- Vantaggio: nessuna chiamata esterna, dati consistenti

**Opzione 2: Scraping da fonti esterne**
- Usa `mstarpy` per recuperare dati da Morningstar
- Usa `justetf-scraping` per recuperare dati da JustETF
- Gestire errori se ISIN non trovato

**Implementazione suggerita:**
```python
def get_etf_performance(isin: str, universe: List[UniverseInstrument]) -> Optional[dict]:
    # Prima cerca nell'universo caricato
    for inst in universe:
        if inst.isin == isin:
            return {
                "name": inst.name,
                "isin": inst.isin,
                "perf_1m": inst.perf_1m,
                "perf_3m": inst.perf_3m,
                # ... altri periodi
            }

    # Se non trovato, cerca su fonti esterne
    return search_external_sources(isin)
```

---

## 4. Formato Output Confronto

### 4.1 Tabella Confronto

| Nome | ISIN | Categoria | Perf. Selezionata | Delta vs ETF | Status |
|------|------|-----------|-------------------|--------------|--------|
| ETF Benchmark | IE00B5BMR087 | - | 45.20% | BENCHMARK | 🎯 |
| Fondo A | LU0123456789 | Az. USA Large Blend | 52.10% | +6.90% | ✅ BATTE |
| Fondo B | IE9876543210 | Az. USA Large Growth | 48.50% | +3.30% | ✅ BATTE |
| Fondo C | FR1111111111 | Az. USA Large Value | 42.00% | -3.20% | ❌ NON BATTE |

### 4.2 Metriche Riepilogative

| Metrica | Valore |
|---------|--------|
| ETF Benchmark | iShares Core S&P 500 (IE00B5BMR087) |
| Periodo Confronto | 3 anni |
| Performance ETF | +45.20% |
| Fondi Analizzati | 342 |
| Fondi che BATTONO l'ETF | 127 (37.1%) |
| Fondi che NON battono l'ETF | 215 (62.9%) |
| Miglior Delta | +18.50% (Fondo XYZ) |
| Peggior Delta | -12.30% (Fondo ABC) |
| Media Delta | +2.15% |

---

## 5. Periodi di Performance

Il sistema supporta i seguenti periodi (gia' implementati in v3.1):

| Periodo | Chiave | Colonna Excel |
|---------|--------|---------------|
| 1 mese | `1m` | Perf. 1m (EUR) |
| 3 mesi | `3m` | Perf. 3m (EUR) |
| 6 mesi | `6m` | Perf. 6m (EUR) |
| YTD | `ytd` | Perf. YTD (EUR) |
| 1 anno | `1y` | Perf. 1a (EUR) |
| 3 anni | `3y` | Perf. 3a (EUR) |
| 5 anni | `5y` | Perf. 5a (EUR) |
| 7 anni | `7y` | Perf. 7a (EUR) |
| 9 anni | `9y` | Perf. 9a (EUR) |
| 10 anni | `10y` | Perf. 10a (EUR) |

---

## 6. Criteri di Accettazione

### 6.1 Funzionalita' Core (Must Have)

- [ ] L'utente puo' selezionare MULTIPLE categorie Morningstar contemporaneamente
- [ ] L'utente puo' inserire l'ISIN di un ETF e avviare il confronto
- [ ] Il sistema calcola il delta performance per ogni fondo vs ETF
- [ ] I fondi che battono l'ETF sono evidenziati in verde
- [ ] I fondi che non battono l'ETF sono evidenziati in rosso
- [ ] La tabella e' ordinata per delta (migliori in alto)
- [ ] L'utente puo' scaricare i risultati in Excel
- [ ] I filtri min/max performance sono stati rimossi
- [ ] Il bug dei filtri che escludono risultati e' stato corretto

### 6.2 UX/UI (Should Have)

- [ ] Metriche riepilogative (quanti battono, quanti no)
- [ ] L'ETF benchmark e' mostrato in evidenza nella tabella
- [ ] Progress bar durante la ricerca dati ETF
- [ ] Messaggio chiaro se ISIN ETF non trovato

### 6.3 Edge Cases

- [ ] Gestione ISIN ETF non valido (formato errato)
- [ ] Gestione ISIN ETF non trovato (nessun dato)
- [ ] Gestione fondi senza performance per il periodo selezionato
- [ ] Gestione universo vuoto o senza categorie

---

## 7. Glossario

| Termine | Definizione |
|---------|-------------|
| **Universo Fondi** | Insieme di ~3000 fondi che Massimo puo' proporre ai clienti |
| **ETF Benchmark** | ETF di riferimento con cui confrontare i fondi |
| **Delta** | Differenza di performance: (Perf. Fondo) - (Perf. ETF) |
| **Batte l'ETF** | Fondo con delta positivo (performance superiore all'ETF) |
| **Non batte l'ETF** | Fondo con delta negativo (performance inferiore all'ETF) |

---

## 8. Changelog da v3.1

| Versione | Data | Modifiche |
|----------|------|-----------|
| 3.1 | 22/01/2026 | Upload Excel con dati completi, filtri base |
| 4.0 | 22/01/2026 | Multiselect categorie, confronto ETF, rimozione filtri min/max |

---

## 9. Approvazioni

| Cliente | Fornitore |
|---------|-----------|
| | |
| _______________________________ | _______________________________ |
| Massimo Zaffanella | Boosha AI |
| Data: _______________ | Data: _______________ |

---

*— Fine Documento —*
