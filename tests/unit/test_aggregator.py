"""
Test per il Data Merger.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from aggregator.data_merger import DataMerger
from core.models import (
    SourceRecord,
    PerformanceData,
    InstrumentType,
    DistributionPolicy,
)


class TestDataMerger:
    """Test per DataMerger."""

    @pytest.fixture
    def merger(self):
        """Istanza DataMerger."""
        return DataMerger()

    @pytest.fixture
    def source_priority(self):
        """Priorità fonti."""
        return ["morningstar", "justetf", "investiny"]

    def test_merge_empty_list(self, merger, source_priority):
        """Test merge lista vuota."""
        result = merger.merge([], source_priority)
        assert result == []

    def test_merge_single_record(self, merger, source_priority, sample_source_record):
        """Test merge singolo record."""
        result = merger.merge([sample_source_record], source_priority)

        assert len(result) == 1
        assert result[0].isin == "IE00B4L5Y983"
        assert result[0].name == "iShares Core MSCI World UCITS ETF"

    def test_merge_multiple_records_same_isin(self, merger, source_priority, multiple_source_records):
        """Test merge record multipli stesso ISIN."""
        result = merger.merge(multiple_source_records, source_priority)

        # Dovrebbero essere 2 ISIN unici
        assert len(result) == 2

        # Trova il record IE00B4L5Y983
        ie_record = next(r for r in result if r.isin == "IE00B4L5Y983")

        # Verifica che le fonti siano aggregate
        assert len(ie_record.sources) == 2
        assert "justetf" in ie_record.sources
        assert "morningstar" in ie_record.sources

    def test_merge_priority_resolution(self, merger, source_priority):
        """Test risoluzione conflitti per priorità."""
        records = [
            SourceRecord(
                isin="IE00B4L5Y983",
                name="Name from JustETF",
                source="justetf",
                performance=PerformanceData(return_1y=15.0),
            ),
            SourceRecord(
                isin="IE00B4L5Y983",
                name="Name from Morningstar",
                source="morningstar",
                category_morningstar="Test Category",
                performance=PerformanceData(return_1y=14.8),
            ),
        ]

        result = merger.merge(records, source_priority)

        # Morningstar ha priorità maggiore, quindi il nome dovrebbe venire da lì
        assert len(result) == 1
        assert result[0].name == "Name from Morningstar"
        # Ma la categoria dovrebbe essere presa da Morningstar
        assert result[0].category_morningstar == "Test Category"

    def test_merge_invalid_isin_skipped(self, merger, source_priority):
        """Test che ISIN invalidi vengono saltati."""
        records = [
            SourceRecord(
                isin="INVALID",
                name="Invalid Record",
                source="test",
            ),
            SourceRecord(
                isin="IE00B4L5Y983",
                name="Valid Record",
                source="test",
            ),
        ]

        result = merger.merge(records, source_priority)

        assert len(result) == 1
        assert result[0].isin == "IE00B4L5Y983"

    def test_quality_score_calculation(self, merger, source_priority):
        """Test calcolo quality score."""
        # Record con molti dati
        complete_record = SourceRecord(
            isin="IE00B4L5Y983",
            name="Complete Record",
            source="justetf",
            category_morningstar="Test",
            performance=PerformanceData(
                ytd=5.0,
                return_1y=10.0,
                return_3y=8.0,
                return_5y=12.0,
                return_10y=15.0,
            ),
        )

        result = merger.merge([complete_record], source_priority)

        # Score dovrebbe essere > 0
        assert result[0].data_quality_score > 0

    def test_best_value_selection(self, merger, source_priority):
        """Test selezione miglior valore."""
        records = [
            SourceRecord(
                isin="IE00B4L5Y983",
                name="Record 1",
                source="justetf",
                performance=PerformanceData(return_1y=None, return_3y=10.0),
            ),
            SourceRecord(
                isin="IE00B4L5Y983",
                name="Record 2",
                source="morningstar",
                performance=PerformanceData(return_1y=15.0, return_3y=None),
            ),
        ]

        result = merger.merge(records, source_priority)

        # Dovrebbe prendere return_1y da morningstar e return_3y da justetf
        assert result[0].perf_1y_eur == 15.0
        assert result[0].perf_3y_eur == 10.0
