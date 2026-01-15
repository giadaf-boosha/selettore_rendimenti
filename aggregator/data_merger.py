"""
Data Merger - Aggregazione e deduplicazione dati via ISIN.

Implementa la logica di merge per combinare record da fonti multiple
in un unico record aggregato per ogni ISIN.
"""
from typing import List, Dict, Optional
from collections import defaultdict
from datetime import datetime
import logging
import re

from core.models import (
    SourceRecord,
    AggregatedInstrument,
    InstrumentType,
    DistributionPolicy,
)

logger = logging.getLogger(__name__)

# Pattern ISIN per validazione
ISIN_PATTERN = re.compile(r'^[A-Z]{2}[A-Z0-9]{9}[0-9]$')


class DataMerger:
    """
    Aggrega e deduplica record da fonti multiple usando ISIN come chiave.

    Implementa strategia di risoluzione conflitti basata su priorità fonte.
    I dati vengono combinati prendendo il valore migliore disponibile
    da ciascuna fonte secondo l'ordine di priorità.
    """

    def merge(
        self,
        records: List[SourceRecord],
        source_priority: List[str]
    ) -> List[AggregatedInstrument]:
        """
        Aggrega record multipli per lo stesso ISIN.

        Args:
            records: Lista di SourceRecord da tutte le fonti
            source_priority: Ordine di priorità fonti per risoluzione conflitti

        Returns:
            Lista di AggregatedInstrument deduplicated
        """
        if not records:
            return []

        # Raggruppa per ISIN
        by_isin: Dict[str, List[SourceRecord]] = defaultdict(list)

        for record in records:
            normalized_isin = record.isin.strip().upper() if record.isin else ""
            if self._validate_isin(normalized_isin):
                by_isin[normalized_isin].append(record)
            else:
                logger.warning(f"Invalid ISIN skipped: {record.isin}")

        # Aggrega ogni gruppo
        aggregated = []
        for isin, isin_records in by_isin.items():
            try:
                merged = self._merge_records(isin, isin_records, source_priority)
                aggregated.append(merged)
            except Exception as e:
                logger.error(f"Failed to merge {isin}: {e}")

        logger.info(f"Merged {len(records)} records into {len(aggregated)} unique instruments")

        return aggregated

    def _validate_isin(self, isin: str) -> bool:
        """
        Valida formato ISIN.

        Args:
            isin: Codice ISIN da validare

        Returns:
            True se valido
        """
        if not isin or len(isin) != 12:
            return False
        return bool(ISIN_PATTERN.match(isin))

    def _merge_records(
        self,
        isin: str,
        records: List[SourceRecord],
        priority: List[str]
    ) -> AggregatedInstrument:
        """
        Merge record per singolo ISIN.

        Args:
            isin: Codice ISIN
            records: Lista record per questo ISIN
            priority: Ordine priorità fonti

        Returns:
            AggregatedInstrument con dati combinati
        """
        # Ordina per priorità fonte
        sorted_records = sorted(
            records,
            key=lambda r: priority.index(r.source) if r.source in priority else 999
        )

        # Record primario (priorità più alta)
        primary = sorted_records[0]

        # Raccogli fonti
        sources = list(set(r.source for r in records))

        # Merge performance (prendi il miglior dato disponibile)
        perf_ytd = self._best_value([r.performance.ytd for r in sorted_records])
        perf_1y = self._best_value([r.performance.return_1y for r in sorted_records])
        perf_3y = self._best_value([r.performance.return_3y for r in sorted_records])
        perf_5y = self._best_value([r.performance.return_5y for r in sorted_records])
        perf_7y = self._best_value([r.performance.return_7y for r in sorted_records])
        perf_10y = self._best_value([r.performance.return_10y for r in sorted_records])

        # Merge metriche rischio
        vol_1y = self._best_value([r.risk.volatility_1y for r in sorted_records])
        vol_3y = self._best_value([r.risk.volatility_3y for r in sorted_records])
        sharpe = self._best_value([r.risk.sharpe_ratio_3y for r in sorted_records])

        # Merge categorie (preferisci valori non-null)
        cat_ms = self._first_non_null([r.category_morningstar for r in sorted_records])
        cat_ag = self._first_non_null([r.category_assogestioni for r in sorted_records])

        # Merge altri campi
        domicile = self._first_non_null([r.domicile for r in sorted_records])
        distribution = self._best_distribution([r.distribution for r in sorted_records])

        # Determina tipo strumento migliore
        inst_type = self._best_instrument_type([r.instrument_type for r in sorted_records])

        # Calcola data quality score
        quality = self._calculate_quality_score(
            perf_ytd, perf_1y, perf_3y, perf_5y, perf_10y,
            vol_3y, sharpe, cat_ms, len(sources)
        )

        return AggregatedInstrument(
            isin=isin,
            name=primary.name,
            instrument_type=inst_type,
            currency=primary.currency,
            domicile=domicile,
            distribution=distribution,
            category_morningstar=cat_ms,
            category_assogestioni=cat_ag,
            perf_ytd_eur=perf_ytd,
            perf_1y_eur=perf_1y,
            perf_3y_eur=perf_3y,
            perf_5y_eur=perf_5y,
            perf_7y_eur=perf_7y,
            perf_10y_eur=perf_10y,
            volatility_1y=vol_1y,
            volatility_3y=vol_3y,
            sharpe_ratio_3y=sharpe,
            sources=sources,
            data_quality_score=quality,
            last_updated=datetime.now(),
        )

    def _best_value(self, values: List[Optional[float]]) -> Optional[float]:
        """Restituisce il primo valore non-null."""
        for v in values:
            if v is not None:
                return v
        return None

    def _first_non_null(self, values: List[Optional[str]]) -> Optional[str]:
        """Restituisce la prima stringa non-null/empty."""
        for v in values:
            if v:
                return v
        return None

    def _best_distribution(
        self,
        values: List[DistributionPolicy]
    ) -> DistributionPolicy:
        """Restituisce il valore distribution più specifico."""
        for v in values:
            if v and v != DistributionPolicy.UNKNOWN:
                return v
        return DistributionPolicy.UNKNOWN

    def _best_instrument_type(
        self,
        values: List[InstrumentType]
    ) -> InstrumentType:
        """Restituisce il tipo strumento più specifico."""
        for v in values:
            if v and v != InstrumentType.UNKNOWN:
                return v
        return InstrumentType.UNKNOWN

    def _calculate_quality_score(
        self,
        *values,
        num_sources: int = 1
    ) -> float:
        """
        Calcola score qualità dati (0-100).

        Basato su:
        - Completezza dei campi (70%)
        - Numero di fonti che confermano i dati (30%)

        Args:
            *values: Valori da verificare per completezza
            num_sources: Numero di fonti dati

        Returns:
            Score 0-100
        """
        # Conta campi non-null
        non_null = sum(1 for v in values if v is not None)
        completeness = non_null / len(values) if values else 0

        # Bonus per multiple fonti (max 30 punti)
        source_bonus = min(num_sources * 10, 30)

        return min(100, completeness * 70 + source_bonus)
