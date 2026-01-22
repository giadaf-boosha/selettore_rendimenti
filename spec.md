# DOCUMENTO DI SPECIFICHE
## Selettore Automatico Rendimenti Fondi/ETF - v3.0

---

| | |
|---|---|
| **Cliente** | Massimo Zaffanella - Consulente Finanziario |
| **Progetto** | AI Acceleration Program - Automazione Back-Office |
| **Data** | 22 gennaio 2026 |
| **Versione** | 3.0 |
| **Deployment** | Streamlit Cloud (https://streamlit.io/) |

---

## 1. Contesto e Obiettivo

### 1.1 Situazione Attuale

Massimo Zaffanella, consulente finanziario, dedica una parte significativa del proprio tempo alla ricerca e al confronto di strumenti finanziari (fondi comuni e ETF) su diverse piattaforme online. Questa attività, sebbene essenziale per fornire consulenza di qualità ai clienti, risulta ripetitiva e time-consuming.

Attualmente il processo prevede:

- Accesso manuale a 5-6 piattaforme diverse (JustETF, Morningstar, Quantalys, Investing.com, FondiDoc)
- Ricerca per categoria, settore o tema di investimento
- Estrazione manuale delle performance su diversi orizzonti temporali
- Consolidamento dei dati in un file Excel per il confronto

La versione 1.0 del sistema ha automatizzato la ricerca multi-piattaforma, ma manca una funzionalità chiave: **la possibilità di confrontare i fondi del proprio portafoglio ("Universo Fondi") con gli ETF di mercato**.

### 1.2 Obiettivo del Progetto (v3.0)

Estendere la web application esistente per permettere a Massimo di:

1. **Caricare il proprio "Universo Fondi"** tramite file Excel (elenco di ISIN dei fondi a sua disposizione)
2. **Confrontare i fondi dell'universo con gli ETF corrispondenti** per categoria Morningstar o Assogestioni
3. **Selezionare un ETF specifico** e confrontarlo con i fondi del proprio universo
4. **Analizzare le performance su orizzonti temporali estesi**: 1-3-6-12 mesi, YTD, 3-5-7-9-10 anni

### 1.3 Principio Guida

> "È fondamentale che io possa, ogni volta inserire il mio Universo, perché è molto più semplice inserirlo di volta in volta tramite un file Excel, rispetto a utilizzare database esterni."
> — Massimo Zaffanella

---

## 2. Requisiti Funzionali

### 2.1 Funzionalità Esistenti (v1.0 - Mantenute)

#### RF-01: Ricerca Multi-Piattaforma
Il sistema interroga automaticamente:
- **JustETF.com** - ETF quotati in Europa
- **Morningstar.com** - ETF e Fondi globali
- **Investing.com** - Dati fondi (via investiny)

#### RF-02: Filtri di Ricerca
- Categoria Morningstar / Assogestioni
- Valuta (EUR, USD, GBP, CHF)
- Tipo strumento (ETF / Fondi)
- Politica distribuzione (Accumulo / Distribuzione)
- Performance minima per periodo

#### RF-03: Output Excel
File Excel formattato con performance, categorie, metriche di rischio.

---

### 2.2 Nuove Funzionalità (v3.0)

#### RF-04: Upload Universo Fondi

| Elemento | Descrizione |
|----------|-------------|
| **Input** | File Excel (.xlsx, .xls) con colonna ISIN |
| **Formato atteso** | Colonna "ISIN" obbligatoria, altre colonne opzionali (Nome, Note, ecc.) |
| **Validazione** | Verifica formato ISIN (12 caratteri, pattern AA + 9 alfanum + 1 digit) |
| **Persistenza** | Nessun database - il file viene caricato ad ogni sessione |
| **Limite** | Max 500 ISIN per file (per performance) |

**Flusso Upload:**
1. L'utente clicca su "Carica Universo Fondi"
2. Seleziona file Excel dal proprio computer
3. Il sistema valida gli ISIN e mostra anteprima
4. L'utente conferma il caricamento
5. L'universo è disponibile per i confronti

#### RF-05: Modalità di Confronto

Il sistema deve supportare **due modalità operative**:

| Modalità | Descrizione | Casi d'uso |
|----------|-------------|------------|
| **A. Universo vs ETF per Categoria** | Seleziona categoria → Confronta fondi universo con ETF della stessa categoria | "Quali dei miei fondi azionari USA hanno fatto meglio dell'ETF equivalente?" |
| **B. ETF vs Universo** | Seleziona un ETF specifico → Confronta con fondi dell'universo di categorie simili | "Come si posiziona questo ETF rispetto ai fondi che ho a disposizione?" |

##### Modalità A: Universo vs ETF per Categoria

**Flusso:**
1. L'utente carica il proprio Universo Fondi (file Excel)
2. Seleziona una categoria (Morningstar o Assogestioni)
3. Clicca "CONFRONTA"
4. Il sistema:
   - Filtra i fondi dell'universo per la categoria selezionata
   - Cerca gli ETF corrispondenti da JustETF/Morningstar
   - Mostra tabella comparativa con performance side-by-side
5. Output: Excel con confronto fondi vs ETF

##### Modalità B: ETF vs Universo

**Flusso:**
1. L'utente carica il proprio Universo Fondi
2. L'utente inserisce l'ISIN di un ETF o lo cerca per nome
3. Il sistema recupera i dati dell'ETF dalle fonti
4. Mostra l'ETF affiancato ai fondi dell'universo (stessa categoria o tutte)
5. Output: Excel con confronto ETF selezionato vs fondi universo

#### RF-06: Periodi di Performance Estesi

Il sistema deve supportare i seguenti periodi di confronto:

| Periodo | Chiave Interna | Note |
|---------|----------------|------|
| 1 mese | `1m` | Nuovo |
| 3 mesi | `3m` | Nuovo |
| 6 mesi | `6m` | Nuovo |
| 12 mesi / 1 anno | `1y` | Esistente |
| YTD | `ytd` | Esistente |
| 3 anni | `3y` | Esistente |
| 5 anni | `5y` | Esistente |
| 7 anni | `7y` | Esistente |
| 9 anni | `9y` | Nuovo |
| 10 anni | `10y` | Esistente |

#### RF-07: Tabella Comparativa

La tabella di confronto deve mostrare:

| Colonna | Descrizione |
|---------|-------------|
| **Nome** | Nome strumento |
| **ISIN** | Codice identificativo |
| **Tipo** | ETF / Fondo |
| **Categoria** | Morningstar / Assogestioni |
| **Origine** | "Universo" o "Mercato" |
| **Perf. 1m** | Performance 1 mese |
| **Perf. 3m** | Performance 3 mesi |
| **Perf. 6m** | Performance 6 mesi |
| **Perf. 1a** | Performance 1 anno |
| **Perf. YTD** | Performance Year-To-Date |
| **Perf. 3a** | Performance 3 anni |
| **Perf. 5a** | Performance 5 anni |
| **Perf. 7a** | Performance 7 anni |
| **Perf. 9a** | Performance 9 anni |
| **Perf. 10a** | Performance 10 anni |
| **Differenza** | Delta performance vs benchmark (ETF) |

#### RF-08: Indicatori Visivi di Confronto

| Indicatore | Condizione | Rappresentazione |
|------------|------------|------------------|
| **Outperformance** | Fondo batte ETF | Verde / Freccia su |
| **Underperformance** | Fondo sotto ETF | Rosso / Freccia giù |
| **Parità** | Differenza < 0.5% | Grigio / Trattino |

---

### 2.3 Interfaccia Utente (v3.0)

#### RF-09: Layout Aggiornato

```
┌─────────────────────────────────────────────────────────────────┐
│ 📊 Selettore Rendimenti Fondi/ETF                               │
├─────────────────┬───────────────────────────────────────────────┤
│                 │                                               │
│  SIDEBAR        │   MAIN CONTENT                                │
│                 │                                               │
│  ┌───────────┐  │   ┌─────────────────────────────────────────┐ │
│  │📁 CARICA  │  │   │ 📊 Il Mio Universo Fondi               │ │
│  │ UNIVERSO  │  │   │ ────────────────────────────────────── │ │
│  │ FONDI     │  │   │ ✅ 45 fondi caricati                   │ │
│  └───────────┘  │   │ Categorie: 8 | Valute: EUR, USD        │ │
│                 │   └─────────────────────────────────────────┘ │
│  ──────────────  │                                               │
│                 │   ┌─────────────────────────────────────────┐ │
│  📌 MODALITA'   │   │ [Tab] Ricerca  [Tab] Confronto         │ │
│  ○ Ricerca      │   ├─────────────────────────────────────────┤ │
│  ◉ Confronto    │   │                                         │ │
│    Universo     │   │  Risultati confronto / Tabella dati    │ │
│                 │   │                                         │ │
│  ──────────────  │   │  ┌────┬────┬────┬────┬────┬────────┐  │ │
│                 │   │  │Nome│ISIN│Tipo│1a  │3a  │Δ vs ETF│  │ │
│  🔍 FILTRI      │   │  ├────┼────┼────┼────┼────┼────────┤  │ │
│  Categoria      │   │  │... │... │... │... │... │ +2.3%  │  │ │
│  [Dropdown]     │   │  └────┴────┴────┴────┴────┴────────┘  │ │
│                 │   │                                         │ │
│  Periodo        │   └─────────────────────────────────────────┘ │
│  [Multi-select] │                                               │
│                 │   ┌─────────────────────────────────────────┐ │
│  ──────────────  │   │ 📥 SCARICA CONFRONTO EXCEL             │ │
│                 │   └─────────────────────────────────────────┘ │
│  [🔎 CONFRONTA] │                                               │
│                 │                                               │
└─────────────────┴───────────────────────────────────────────────┘
```

#### RF-10: Componenti UI Nuovi

| Componente | Tipo Streamlit | Descrizione |
|------------|----------------|-------------|
| Upload Universo | `st.file_uploader` | Caricamento file Excel |
| Anteprima Universo | `st.dataframe` | Mostra ISIN caricati |
| Selettore Modalità | `st.radio` | Ricerca / Confronto |
| Selettore Periodi | `st.multiselect` | Selezione multipla periodi |
| Ricerca ETF | `st.text_input` + `st.selectbox` | Ricerca per ISIN o nome |
| Tabella Confronto | `st.dataframe` con `column_config` | Colori condizionali |
| Metriche Riepilogo | `st.metric` | Media, best, worst delta |

---

## 3. Requisiti Tecnici

### 3.1 Architettura (v3.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Streamlit)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Upload    │  │   Filtri    │  │   Tabella Confronto     │  │
│  │  Universo   │  │   Ricerca   │  │   + Download Excel      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    BUSINESS LOGIC                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Universe   │  │   Search    │  │   Comparison Engine     │  │
│  │   Loader    │  │   Engine    │  │   (NUOVO)               │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│                    DATA LAYER                                    │
│  ┌───────────┐  ┌────────────┐  ┌───────────┐  ┌─────────────┐  │
│  │  JustETF  │  │ Morningstar│  │ Investiny │  │  Universe   │  │
│  │  Scraper  │  │  Scraper   │  │  Scraper  │  │  Parser     │  │
│  └───────────┘  └────────────┘  └───────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Nuovi Moduli da Implementare

| Modulo | Path | Responsabilità |
|--------|------|----------------|
| `universe_loader.py` | `core/` | Parsing Excel universo, validazione ISIN |
| `comparison_engine.py` | `orchestrator/` | Logica confronto fondi vs ETF |
| `comparison_exporter.py` | `exporters/` | Export Excel con formato confronto |

### 3.3 Modifiche ai Moduli Esistenti

| Modulo | Modifiche |
|--------|-----------|
| `config.py` | Aggiungere periodi 1m, 3m, 6m, 9y |
| `core/models.py` | Estendere PerformanceData con nuovi periodi |
| `app.py` | Nuova sezione upload + tab confronto |
| `scrapers/*.py` | Supporto nuovi periodi (se disponibili dalle fonti) |

### 3.4 Stack Tecnologico (Invariato)

| Componente | Tecnologia |
|------------|------------|
| Linguaggio | Python 3.11 |
| Frontend | Streamlit 1.30+ |
| Data Processing | pandas 2.0+ |
| Export Excel | openpyxl, xlsxwriter |
| Scraping | justetf-scraping, mstarpy, investiny |
| Deployment | **Streamlit Cloud** |

### 3.5 Considerazioni Deployment Streamlit Cloud

| Aspetto | Gestione |
|---------|----------|
| **File temporanei** | Usare `st.session_state` per persistere universo durante sessione |
| **Limiti risorse** | Max 500 ISIN per universo, timeout 30s per operazione |
| **Secrets** | Nessuno richiesto (dati pubblici) |
| **Cache** | `@st.cache_data` per risultati ricerche |

---

## 4. Piano di Implementazione

### Fase 1: Estensione Modelli e Configurazione (2 ore)

**Obiettivi:**
- Aggiungere nuovi periodi di performance (1m, 3m, 6m, 9y)
- Creare modelli dati per Universo Fondi

**Deliverable:**
- `config.py` aggiornato con nuovi periodi
- `core/models.py` esteso con `UniverseInstrument` e periodi aggiuntivi

### Fase 2: Universe Loader (3 ore)

**Obiettivi:**
- Implementare parsing file Excel universo
- Validazione ISIN
- Integrazione con UI upload

**Deliverable:**
- `core/universe_loader.py` completo
- Widget upload funzionante in `app.py`

### Fase 3: Comparison Engine (4 ore)

**Obiettivi:**
- Implementare logica confronto Universo vs ETF
- Implementare logica confronto ETF vs Universo
- Calcolo delta performance

**Deliverable:**
- `orchestrator/comparison_engine.py` completo
- Test unitari per logica confronto

### Fase 4: UI Confronto (3 ore)

**Obiettivi:**
- Implementare tab/sezione confronto
- Tabella comparativa con indicatori visivi
- Selezione multipla periodi

**Deliverable:**
- `app.py` con nuova sezione confronto
- UI funzionante per entrambe le modalità

### Fase 5: Export Confronto Excel (2 ore)

**Obiettivi:**
- Creare template Excel per confronto
- Formattazione condizionale per delta
- Foglio riepilogo con statistiche

**Deliverable:**
- `exporters/comparison_exporter.py` completo
- Download Excel confronto funzionante

### Fase 6: Testing e Deploy (2 ore)

**Obiettivi:**
- Test end-to-end con file Excel reali
- Deploy su Streamlit Cloud
- Documentazione utente aggiornata

**Deliverable:**
- Applicazione deployata e funzionante
- Test superati con dati reali

---

## 5. Formato File Excel Universo (Input)

### 5.1 Struttura Minima Richiesta

| Colonna | Obbligatoria | Formato | Esempio |
|---------|--------------|---------|---------|
| **ISIN** | ✅ Sì | 12 caratteri | IE00B4L5Y983 |
| Nome | No | Testo | iShares Core MSCI World |
| Categoria | No | Testo | Azionari Globali |
| Note | No | Testo | Preferito per PAC |

### 5.2 Esempio File

```
| ISIN         | Nome                      | Categoria           | Note          |
|--------------|---------------------------|---------------------|---------------|
| LU0322253906 | Xtrackers MSCI World      | Azionari Globali    | Core          |
| IE00B4L5Y983 | iShares Core MSCI World   | Azionari Globali    | Alternativa   |
| FR0010315770 | Lyxor S&P 500             | Azionari USA        | -             |
```

### 5.3 Messaggi di Errore

| Errore | Messaggio |
|--------|-----------|
| Colonna ISIN mancante | "Il file deve contenere una colonna 'ISIN'" |
| ISIN formato invalido | "ISIN '{valore}' non valido (riga {n})" |
| File vuoto | "Il file non contiene ISIN validi" |
| Troppi ISIN | "Limite massimo 500 ISIN superato" |

---

## 6. Criteri di Accettazione

### 6.1 Funzionalità Core (Must Have)

- [ ] L'utente può caricare un file Excel con ISIN dei propri fondi
- [ ] Il sistema valida gli ISIN e mostra quelli validi/invalidi
- [ ] L'utente può selezionare una categoria e confrontare fondi universo vs ETF
- [ ] L'utente può selezionare un ETF e confrontarlo con i fondi universo
- [ ] La tabella mostra le performance su tutti i periodi richiesti (1m-10a)
- [ ] Il sistema calcola e mostra il delta performance (fondo vs ETF)
- [ ] L'utente può scaricare un Excel con il confronto completo
- [ ] L'applicazione funziona correttamente su Streamlit Cloud

### 6.2 UX/UI (Should Have)

- [ ] Indicatori visivi (colori) per outperformance/underperformance
- [ ] Metriche riepilogative (media delta, best performer, worst performer)
- [ ] L'universo persiste durante la sessione senza ricaricare
- [ ] Progress bar durante le operazioni di ricerca/confronto
- [ ] Messaggi di errore chiari e user-friendly

### 6.3 Performance (Nice to Have)

- [ ] Tempo caricamento universo < 5 secondi per 100 ISIN
- [ ] Tempo confronto < 60 secondi per categoria
- [ ] Cache risultati per evitare ricerche duplicate

---

## 7. Glossario

| Termine | Definizione |
|---------|-------------|
| **Universo Fondi** | Insieme di fondi/strumenti che l'utente ha a disposizione, caricato via Excel |
| **Confronto** | Analisi comparativa delle performance tra fondi universo ed ETF di mercato |
| **Delta** | Differenza di performance tra un fondo e l'ETF benchmark |
| **Outperformance** | Quando un fondo supera la performance dell'ETF di riferimento |
| **Underperformance** | Quando un fondo ha performance inferiore all'ETF di riferimento |

---

## 8. Appendice: Mapping Categorie

Per il confronto, le categorie dell'universo vengono mappate con le categorie ETF:

| Categoria Fondo | Categoria ETF Corrispondente |
|-----------------|------------------------------|
| AZ. AMERICA | Azionari USA Large Cap Blend |
| AZ. EUROPA | Azionari Europa Large Cap Blend |
| AZ. INTERNAZIONALI | Azionari Globali Large Cap Blend |
| AZ. PAESI EMERGENTI | Azionari Paesi Emergenti |
| OBBL. EURO GOV. | Obbligazionari EUR Governativi |
| ... | ... |

*(Mapping completo da definire in fase di implementazione)*

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
