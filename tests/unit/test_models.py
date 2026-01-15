"""
Test per i modelli dati.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.models import (
    SourceRecord,
    AggregatedInstrument,
    SearchCriteria,
    PerformanceData,
    InstrumentType,
    DistributionPolicy,
)


class TestSourceRecord:
    """Test per SourceRecord."""

    def test_validate_isin_valid(self, sample_source_record):
        """Test validazione ISIN valido."""
        assert sample_source_record.validate_isin() is True

    def test_validate_isin_invalid_short(self):
        """Test validazione ISIN troppo corto."""
        record = SourceRecord(
            isin="INVALID",
            name="Test",
            source="test"
        )
        assert record.validate_isin() is False

    def test_validate_isin_invalid_format(self):
        """Test validazione ISIN formato errato."""
        record = SourceRecord(
            isin="123456789012",
            name="Test",
            source="test"
        )
        assert record.validate_isin() is False

    @pytest.mark.parametrize("isin,expected", [
        ("IE00B4L5Y983", True),
        ("LU0392494562", True),
        ("US0378331005", True),
        ("INVALID", False),
        ("", False),
        ("ie00b4l5y983", False),  # lowercase
    ])
    def test_validate_isin_parametrized(self, isin, expected):
        """Test parametrizzato validazione ISIN."""
        record = SourceRecord(isin=isin, name="Test", source="test")
        assert record.validate_isin() == expected


class TestPerformanceData:
    """Test per PerformanceData."""

    def test_get_by_period(self):
        """Test recupero performance per periodo."""
        perf = PerformanceData(
            ytd=5.0,
            return_1y=10.0,
            return_3y=8.0,
            return_5y=12.0,
        )

        assert perf.get_by_period("ytd") == 5.0
        assert perf.get_by_period("1y") == 10.0
        assert perf.get_by_period("3y") == 8.0
        assert perf.get_by_period("5y") == 12.0
        assert perf.get_by_period("10y") is None
        assert perf.get_by_period("invalid") is None


class TestSearchCriteria:
    """Test per SearchCriteria."""

    def test_to_dict(self, sample_search_criteria):
        """Test serializzazione a dict."""
        result = sample_search_criteria.to_dict()

        assert isinstance(result, dict)
        assert "categories_ms" in result
        assert "currencies" in result
        assert result["currencies"] == ["EUR"]

    def test_has_category_filter_true(self, sample_search_criteria):
        """Test has_category_filter con categorie."""
        assert sample_search_criteria.has_category_filter() is True

    def test_has_category_filter_false(self):
        """Test has_category_filter senza categorie."""
        criteria = SearchCriteria()
        assert criteria.has_category_filter() is False


class TestAggregatedInstrument:
    """Test per AggregatedInstrument."""

    def test_get_performance_by_period(self, sample_aggregated_instrument):
        """Test recupero performance per periodo."""
        inst = sample_aggregated_instrument

        assert inst.get_performance_by_period("ytd") == 8.25
        assert inst.get_performance_by_period("5y") == 11.64
        assert inst.get_performance_by_period("7y") is None

    def test_to_dict(self, sample_aggregated_instrument):
        """Test conversione a dict per export."""
        result = sample_aggregated_instrument.to_dict()

        assert isinstance(result, dict)
        assert result["ISIN"] == "IE00B4L5Y983"
        assert result["Nome"] == "iShares Core MSCI World UCITS ETF"
        assert "Perf. 5a" in result
