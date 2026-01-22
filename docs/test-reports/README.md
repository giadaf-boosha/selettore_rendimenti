# Test Reports

Questa directory contiene i report dei test eseguiti sull'applicazione Selettore Rendimenti Fondi/ETF.

## Struttura

Ogni report segue la nomenclatura: `TEST_REPORT_YYYY-MM-DD.md`

## Report Disponibili

| Data | Versione | Commit | Esito |
|------|----------|--------|-------|
| 2026-01-22 | v3.0.0 | `ec47189` | ⚠️ UI OK, Backend issues |

## Formato Report

Ogni report include:

1. **Informazioni Test** - Data, versione, commit, ambiente
2. **Requisiti Testati** - Lista dei requisiti cliente verificati
3. **Risultati UI** - Test delle funzionalità dell'interfaccia
4. **Risultati Backend** - Test delle funzionalità server-side
5. **Problemi Rilevati** - Issues trovati durante il test
6. **Screenshot** - Evidenze visive dei test
7. **Conclusioni** - Sintesi e raccomandazioni

## Come Eseguire Nuovi Test

I test vengono eseguiti utilizzando Playwright MCP per automatizzare l'interazione con l'app deployata su Streamlit Cloud.

```bash
# L'app viene testata all'URL di produzione
https://giadaf-boosha-selettore-rendimenti-app-quikgb.streamlit.app/
```

## Screenshot

Gli screenshot dei test sono salvati in `.playwright-mcp/test_screenshots/` e referenziati nei report.
