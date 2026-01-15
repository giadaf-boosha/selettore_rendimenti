# DOCUMENTO DI SPECIFICHE
## Selettore Automatico Rendimenti Fondi/ETF

---

| | |
|---|---|
| **Cliente** | Massimo Zaffanella - Consulente Finanziario |
| **Progetto** | AI Acceleration Program - Automazione Back-Office |
| **Data** | 16 gennaio 2026 |
| **Versione** | 2.0 |

---

## 1. Contesto e Obiettivo

### 1.1 Situazione Attuale

Massimo Zaffanella, consulente finanziario, dedica una parte significativa del proprio tempo alla ricerca e al confronto di strumenti finanziari (fondi comuni e ETF) su diverse piattaforme online. Questa attività, sebbene essenziale per fornire consulenza di qualità ai clienti, risulta ripetitiva e time-consuming.

Attualmente il processo prevede:

- Accesso manuale a 5-6 piattaforme diverse (JustETF, Morningstar, Quantalys, Investing.com, FondiDoc)
- Ricerca per categoria, settore o tema di investimento
- Estrazione manuale delle performance su diversi orizzonti temporali
- Consolidamento dei dati in un file Excel per il confronto

### 1.2 Obiettivo del Progetto

Creare una **web application user-friendly** che permetta a Massimo di selezionare criteri di ricerca tramite un'interfaccia grafica intuitiva, **senza necessità di competenze tecniche**, e ottenere automaticamente un file Excel con i risultati aggregati dalle principali piattaforme finanziarie.

---

## 2. Requisiti Funzionali

### 2.1 Interfaccia Utente (Streamlit)

L'applicazione deve essere accessibile via browser web e presentare un'interfaccia semplice e intuitiva, utilizzabile senza competenze tecniche.

#### RF-01: Schermata Principale

La schermata principale deve contenere:

| Elemento UI | Tipo | Descrizione |
|-------------|------|-------------|
| Titolo applicazione | Testo | "Selettore Rendimenti Fondi/ETF" |
| Selezione Categoria | Dropdown / Multiselect | Categoria Assogestioni o Morningstar |
| Filtro Valuta | Checkbox multipli | EUR, USD, GBP, CHF |
| Filtro Distribuzione | Radio button | Tutti / Solo distribuzione / Solo accumulo |
| Performance minima | Slider o input numerico | Soglia % per periodo selezionato |
| Periodo performance | Dropdown | YTD, 1a, 3a, 5a, 10a |
| Pulsante CERCA | Button primario | Avvia la ricerca |
| Indicatore progresso | Progress bar | Mostra avanzamento ricerca |
| Tabella risultati | Dataframe interattivo | Anteprima risultati con ordinamento |
| Pulsante SCARICA | Button download | Download file Excel |

#### RF-02: Flusso Utente

Il flusso di utilizzo deve essere lineare e guidato:

1. L'utente apre l'applicazione nel browser (URL locale o cloud)
2. Seleziona i criteri di ricerca dai menu a tendina e filtri
3. Clicca sul pulsante **"CERCA"**
4. Visualizza la progress bar durante l'elaborazione
5. Vede l'anteprima dei risultati in tabella
6. Può ordinare/filtrare la tabella cliccando sulle colonne
7. Clicca **"SCARICA EXCEL"** per ottenere il file

---

### 2.2 Funzionalità Backend

#### RF-03: Ricerca Multi-Piattaforma

Il sistema deve interrogare automaticamente le seguenti piattaforme:

| Piattaforma | Tipo | Priorità | Metodo Accesso |
|-------------|------|----------|----------------|
| **JustETF.com** | ETF | 🟢 ALTA | justetf-scraping (Python) |
| **Morningstar.com** | ETF + Fondi | 🟢 ALTA | mstarpy (Python) |
| **Investing.com** | Fondi | 🟢 ALTA | investpy (Python) |
| **Quantalys.it** | ETF + Fondi | 🟡 MEDIA | Sviluppo custom (opzionale) |
| **FondiDoc.it** | Fondi | 🔴 ESCLUSO | ToS restrittivi |

#### RF-04: Criteri di Ricerca Backend

Il backend deve supportare i seguenti filtri:

| Criterio | Descrizione | Esempio |
|----------|-------------|---------|
| Categoria Assogestioni | Classificazione italiana ufficiale | AZ. ENERGIA E MAT. PRIME |
| Categoria Morningstar | Classificazione internazionale | Azionari Settore Metalli Preziosi |
| Valuta | Valuta di denominazione | EUR, USD |
| Classe di Prezzo | Classe dello strumento | A, B, C, D, I, N |
| Distribuzione | Cedole/dividendi | SI / NO |
| Performance Minima | Soglia di rendimento per periodo | > 50% a 5 anni |

#### RF-05: Output Strutturato

Il sistema deve restituire un file Excel con le seguenti colonne:

| Campo | Descrizione | Tipo |
|-------|-------------|------|
| **Nome** | Nome completo dello strumento | Testo |
| **ISIN** | Codice identificativo univoco (chiave primaria) | Testo (12 caratteri) |
| **Categoria Assogestioni** | Classificazione italiana | Testo |
| **Categoria Morningstar** | Classificazione internazionale | Testo |
| **Valuta** | Valuta di denominazione | Testo (3 caratteri) |
| **Perf. YTD (EUR)** | Performance Year-To-Date in EUR | Percentuale |
| **Perf. 1a / 3a / 5a / 7a / 10a** | Performance su diversi orizzonti temporali | Percentuale |
| **Fonte** | Piattaforma da cui proviene il dato | Testo |

---

## 3. Requisiti Tecnici

### 3.1 Architettura

L'applicazione sarà una web app single-page basata su Streamlit, con architettura a tre layer:

1. **Frontend (Streamlit):** Interfaccia grafica con form, tabelle e download
2. **Business Logic (Python):** Orchestrazione ricerche e aggregazione dati
3. **Data Layer (API/Scraping):** Connettori alle piattaforme finanziarie

### 3.2 Stack Tecnologico

| Componente | Tecnologia | Note |
|------------|------------|------|
| Linguaggio | Python 3.10+ | Compatibilità librerie |
| **Frontend** | **Streamlit 1.30+** | `pip install streamlit` |
| Libreria JustETF | justetf-scraping | `pip install justetf-scraping` |
| Libreria Morningstar | mstarpy | `pip install mstarpy` |
| Libreria Investing | investpy | `pip install investpy` |
| Gestione dati | pandas | Aggregazione e export |
| Output Excel | openpyxl + xlsxwriter | Formattazione avanzata |

### 3.3 Deployment e Accesso

L'applicazione potrà essere eseguita in due modalità:

| Modalità | Descrizione | Accesso |
|----------|-------------|---------|
| **Locale** | Esecuzione sul PC di Massimo | http://localhost:8501 |
| **Cloud** | Hosting su Streamlit Community Cloud | URL pubblico (gratuito) |

**Per l'esecuzione locale, Massimo dovrà:**

1. Aprire il terminale (o prompt dei comandi)
2. Digitare: **`streamlit run app.py`**
3. Il browser si aprirà automaticamente con l'applicazione

### 3.4 Vincoli e Limitazioni

- **Rate Limits:** Rispettare i limiti delle piattaforme (max 1 req/sec per JustETF, ~60 req/min per Investing.com)
- **Dati pubblici:** Utilizzare solo dati accessibili senza autenticazione
- **FondiDoc escluso:** ToS non consentono scraping automatico
- **Connessione internet:** Richiesta per interrogare le piattaforme

---

## 4. Piano di Sviluppo

### 4.1 Fasi e Deliverable

#### 🔹 FASE 1: Backend Core (8 ore)

- Integrazione JustETF (ETF)
- Integrazione Morningstar (ETF + Fondi)
- Integrazione Investing.com (Fondi)
- Logica di aggregazione dati via ISIN
- **Deliverable:** Modulo Python funzionante

#### 🔹 FASE 2: Frontend Streamlit (8 ore)

- Creazione interfaccia grafica con tutti i filtri
- Progress bar durante l'elaborazione
- Tabella risultati interattiva (ordinamento, filtri)
- Pulsante download Excel
- **Deliverable:** Web app funzionante in locale

#### 🔹 FASE 3: Output e UX Polish (6 ore)

- Formattazione Excel professionale (colori, filtri auto)
- Messaggi di errore user-friendly
- Help contestuale e tooltip sui filtri
- **Deliverable:** Applicazione pronta per utente finale

#### 🔹 FASE 4: Testing e Deploy (6 ore)

- Test con ISIN campione dal file Excel di Massimo
- Validazione dati vs. fonti manuali
- Configurazione ambiente sul PC di Massimo
- Documentazione utente (guida rapida)
- **Deliverable:** Sistema in produzione + manuale utente

### 4.2 Estensioni Future (Opzionali)

| Estensione | Effort | Dipendenze |
|------------|--------|------------|
| Deploy su Streamlit Cloud | 2-4 ore | Account GitHub |
| Scraper custom per Quantalys | 8-16 ore | Reverse engineering |
| Salvataggio ricerche preferite | 4 ore | Database locale |
| Automazione aggiornamento sito | Da quotare | n8n / Make |

---

## 5. Stima Effort e Budget

### 5.1 Riepilogo Ore

| Attività | Ore | Priorità |
|----------|-----|----------|
| Fase 1: Backend Core | 8 | 🟢 ALTA |
| Fase 2: Frontend Streamlit | 8 | 🟢 ALTA |
| Fase 3: Output e UX Polish | 6 | 🟡 MEDIA |
| Fase 4: Testing e Deploy | 6 | 🟢 ALTA |
| **TOTALE PROGETTO** | **28** | - |

---

## 6. Criteri di Accettazione

Il progetto sarà considerato completato quando:

- [ ] L'applicazione Streamlit si avvia correttamente e mostra l'interfaccia grafica
- [ ] Tutti i filtri funzionano e influenzano i risultati della ricerca
- [ ] Lo script interroga correttamente JustETF, Morningstar e Investing.com
- [ ] L'output Excel contiene tutte le colonne definite nella sezione RF-05
- [ ] I dati sono aggregati correttamente via ISIN (no duplicati)
- [ ] Le performance sono espresse in EUR e corrispondono alle fonti originali
- [ ] Test superato su almeno 50 ISIN dal file Excel di Massimo
- [ ] Massimo è in grado di avviare e utilizzare l'app autonomamente
- [ ] Documentazione utente consegnata (guida rapida PDF)

---

## 7. Approvazioni

| Cliente | Fornitore |
|---------|-----------|
| | |
| _______________________________ | _______________________________ |
| Massimo Zaffanella | Boosha AI |
| Data: _______________ | Data: _______________ |

---

*— Fine Documento —*
