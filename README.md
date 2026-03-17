<div align="center">

# Selettore Rendimenti Fondi/ETF

**Confronta i tuoi fondi comuni con gli ETF benchmark e scopri chi batte il mercato.**

[![Streamlit App](https://img.shields.io/badge/Streamlit-Live_App-FF4B4B?logo=streamlit&logoColor=white)](https://giadaf-boosha-selettore-rendimenti-app-quikgb.streamlit.app)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Version](https://img.shields.io/badge/version-4.1.0-blue)](https://github.com/giadaf-boosha/selettore_rendimenti)
[![Status](https://img.shields.io/badge/status-stable-brightgreen)]()
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

[**Prova l'App**](https://giadaf-boosha-selettore-rendimenti-app-quikgb.streamlit.app) · [**Quick Start**](#-quick-start) · [**Funzionalita**](#-key-features) · [**Contribuisci**](#-contributing)

</div>

---

## Overview

I consulenti finanziari lavorano con universi di migliaia di fondi e devono rispondere a una domanda ricorrente: **quali fondi battono l'ETF di riferimento?**

Selettore Rendimenti automatizza questa analisi. Carica un file Excel con i dati dei fondi, seleziona una categoria Morningstar, inserisci l'ISIN di un ETF benchmark e ottieni immediatamente la classifica con delta di performance.

**Quando usarlo:**
- Hai un export Excel con performance di fondi da una piattaforma finanziaria
- Vuoi filtrare per categoria Morningstar e/o SFDR
- Vuoi confrontare i fondi filtrati contro un ETF benchmark
- Vuoi esportare i risultati in Excel per i tuoi clienti

---

## ✨ Key Features

- **Upload Universo Fondi** — Carica file Excel con dati completi (nome, ISIN, performance multi-periodo, categorie, costi)
- **Filtri Multi-Categoria** — Seleziona una o piu categorie Morningstar e/o SFDR con logica OR
- **Confronto vs ETF Benchmark** — Inserisci l'ISIN di un ETF e vedi chi lo batte su qualsiasi periodo (1m → 10a)
- **Ranking Automatico** — Ordina i fondi per performance su 10 periodi temporali diversi
- **Pre-caricamento ETF** — Carica fino a 15 ETF benchmark in cache (valida 24h) per ricerche istantanee
- **Export Excel** — Scarica risultati filtrati e confronti in formato `.xlsx`
- **Statistiche per Categoria** — Media, migliore e conteggio fondi per ogni categoria Morningstar

---

## 🚀 Quick Start

```bash
# Clona il repository
git clone https://github.com/giadaf-boosha/selettore_rendimenti.git
cd selettore_rendimenti

# Crea ambiente virtuale e installa dipendenze
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Avvia l'app
streamlit run app.py
```

L'app si apre nel browser su `http://localhost:8501`.

---

## 📦 Installation

### Requisiti

| Requisito | Versione |
|-----------|----------|
| Python    | >= 3.11  |
| pip       | >= 22.0  |

### Dipendenze principali

| Pacchetto      | Uso                          |
|----------------|------------------------------|
| `streamlit`    | Interfaccia web              |
| `pandas`       | Elaborazione dati            |
| `openpyxl`     | Lettura file Excel (.xlsx)   |
| `xlsxwriter`   | Export risultati in Excel    |
| `requests`     | Chiamate HTTP per scraping   |
| `tenacity`     | Retry logic con backoff      |
| `python-dotenv`| Variabili d'ambiente         |

### Scraper esterni (opzionali)

Per abilitare la ricerca di ETF da fonti esterne (JustETF, Morningstar), installa:

```bash
pip install "justetf-scraping @ git+https://github.com/druzsan/justetf-scraping.git@d6e5d04"
pip install "mstarpy>=4.0.0,<9.0.0"
pip install "investiny>=0.7.0"
```

> **NOTE:** L'app funziona anche senza questi pacchetti. Gli ETF possono essere cercati nell'universo caricato o pre-caricati in cache dalla sidebar.

---

## 🧑‍💻 Usage

### 1. Prepara il file Excel

Il file deve contenere almeno una colonna `ISIN`. Colonne supportate:

| Colonna                | Esempio           | Obbligatoria |
|------------------------|-------------------|:------------:|
| ISIN                   | `IE00B4L5Y983`    | Si           |
| Nome                   | `iShares MSCI...` | No           |
| Categoria Morningstar  | `Azionari USA...` | No           |
| Categoria SFDR         | `Art. 8`          | No           |
| Perf. YTD (EUR)        | `0.0523`          | No           |
| Perf. 1m/3m/6m/1a/...  | `0.1245`          | No           |
| Comm. Gest.+Distr.     | `0.015`           | No           |
| VaR Adeg. 3m           | `-0.08`           | No           |

Le performance possono essere in formato decimale (`0.1920` = 19.20%) o percentuale (`19.20` = 19.20%). La normalizzazione e automatica.

### 2. Carica e filtra

1. Nella **sidebar**, carica il file Excel
2. Seleziona una o piu **categorie Morningstar**
3. Opzionalmente filtra per **categoria SFDR**
4. Scegli il **periodo di ordinamento** e clicca **APPLICA FILTRI**

### 3. Confronta con ETF

1. Nella sezione **Confronta con ETF Benchmark**, inserisci l'ISIN dell'ETF
2. Seleziona il **periodo di confronto**
3. Clicca **CONFRONTA**
4. Visualizza metriche: quanti fondi battono l'ETF, media delta, migliore/peggiore
5. **Scarica** i risultati in Excel

### 4. Pre-carica ETF (opzionale)

Per velocizzare i confronti successivi:

1. Nella sidebar, sezione **Prepara ETF Benchmark**
2. Inserisci gli ISIN degli ETF (uno per riga o separati da virgola)
3. Clicca **PREPARA ETF** — i dati restano in cache per 24 ore

---

## ⚙️ Configuration

L'app si configura tramite variabili d'ambiente (file `.env`):

| Variabile               | Default  | Descrizione                              |
|-------------------------|----------|------------------------------------------|
| `DEBUG`                 | `false`  | Abilita modalita debug                   |
| `LOG_LEVEL`             | `INFO`   | Livello di logging (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `CACHE_TTL`             | `3600`   | TTL cache generale (secondi)             |
| `JUSTETF_RATE_LIMIT`    | `2.0`    | Rate limit JustETF (secondi tra richieste) |
| `MORNINGSTAR_RATE_LIMIT`| `2.0`    | Rate limit Morningstar                   |
| `JUSTETF_TIMEOUT`       | `90`     | Timeout richieste JustETF (secondi)      |
| `MORNINGSTAR_TIMEOUT`   | `60`     | Timeout richieste Morningstar (secondi)  |

---

## 🏗 Architecture

```
selettore_rendimenti/
├── app.py                    # Entry point Streamlit
├── config.py                 # Configurazione globale e costanti
├── requirements.txt
├── core/
│   ├── models.py             # Dataclass: UniverseInstrument, ComparisonReport, ...
│   ├── universe_loader.py    # Parser Excel con auto-detect colonne
│   ├── etf_benchmark.py      # Ricerca ETF: universo → cache → fonti esterne
│   └── comparison_calculator.py  # Calcolo delta performance vs benchmark
├── scrapers/
│   ├── base.py               # Interfaccia astratta per scraper
│   ├── justetf_scraper.py    # Scraper JustETF (3400+ ETF europei)
│   └── morningstar_scraper.py # Scraper Morningstar (fondi + ETF)
└── utils/
    ├── http_config.py        # User-Agent e timeout per requests
    ├── logger.py             # Setup logging
    ├── retry.py              # Decorator retry con exponential backoff
    └── validators.py         # Validazione ISIN e dati finanziari
```

**Flusso dati:**

1. L'utente carica un Excel → `UniverseLoader` parsa e produce `List[UniverseInstrument]`
2. I filtri riducono la lista per categoria/SFDR
3. Il confronto ETF cerca il benchmark (universo → cache → scraper esterni) e calcola i delta
4. I risultati vengono visualizzati in Streamlit ed esportabili in Excel

---

## 🛣 Roadmap / Project Status

**Status: Stable (v4.1.0)**

| Funzionalita                     | Status         |
|----------------------------------|:--------------:|
| Upload universo da Excel         | ✅ Stabile     |
| Filtri Morningstar multi-select  | ✅ Stabile     |
| Confronto vs ETF benchmark       | ✅ Stabile     |
| Pre-caricamento ETF in cache     | ✅ Stabile     |
| Export Excel                     | ✅ Stabile     |
| Scraper JustETF                  | ⚠️ Opzionale  |
| Scraper Morningstar              | ⚠️ Opzionale  |
| Grafici comparativi              | 🔜 Pianificato |
| Analisi multi-benchmark          | 🔜 Pianificato |

---

## 🤝 Contributing

I contributi sono benvenuti. Per contribuire:

1. Fai fork del repository
2. Crea un branch per la feature (`git checkout -b feature/nome-feature`)
3. Scrivi codice e test
4. Assicurati che i test passino: `pytest`
5. Apri una Pull Request

```bash
# Setup sviluppo
git clone https://github.com/giadaf-boosha/selettore_rendimenti.git
cd selettore_rendimenti
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-cov responses

# Esegui test
pytest
```

> **WARNING:** Non committare file `.env`, credenziali o dati Excel con informazioni reali dei clienti.

---

## 📄 License

MIT License. Vedi [LICENSE](LICENSE) per i dettagli.

---

<div align="center">

Sviluppato da [Boosha AI](https://github.com/giadaf-boosha)

</div>
