"""
Fixtures pytest per Selettore Rendimenti Fondi/ETF.
"""
import pytest
import json
from pathlib import Path
from decimal import Decimal
from typing import List
import sys

# Aggiungi la directory root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.models import (
    SourceRecord,
    AggregatedInstrument,
    SearchCriteria,
    PerformanceData,
    RiskMetrics,
    InstrumentType,
    DistributionPolicy,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def sample_isin_list() -> List[str]:
    """Carica lista di 50 ISIN campione per i test."""
    with open(FIXTURES_DIR / "sample_isin.json") as f:
        data = json.load(f)
    return data["isin_list"]


@pytest.fixture
def sample_source_record() -> SourceRecord:
    """Crea un SourceRecord di esempio per test unitari."""
    return SourceRecord(
        isin="IE00B4L5Y983",
        name="iShares Core MSCI World UCITS ETF",
        source="justetf",
        instrument_type=InstrumentType.ETF,
        currency="EUR",
        domicile="Ireland",
        distribution=DistributionPolicy.ACCUMULATING,
        category_morningstar="Global Large-Cap Blend Equity",
        category_assogestioni="AZ. INTERNAZIONALI",
        ter=0.20,
        performance=PerformanceData(
            ytd=8.25,
            return_1y=15.30,
            return_3y=10.50,
            return_5y=11.64,
            return_10y=12.80,
        ),
        risk=RiskMetrics(
            volatility_1y=12.5,
            volatility_3y=14.2,
            sharpe_ratio_3y=0.74,
        ),
    )


@pytest.fixture
def sample_aggregated_instrument() -> AggregatedInstrument:
    """Crea un AggregatedInstrument di esempio per test."""
    return AggregatedInstrument(
        isin="IE00B4L5Y983",
        name="iShares Core MSCI World UCITS ETF",
        instrument_type=InstrumentType.ETF,
        currency="EUR",
        domicile="Ireland",
        distribution=DistributionPolicy.ACCUMULATING,
        category_morningstar="Global Large-Cap Blend Equity",
        category_assogestioni="AZ. INTERNAZIONALI",
        perf_ytd_eur=8.25,
        perf_1y_eur=15.30,
        perf_3y_eur=10.50,
        perf_5y_eur=11.64,
        perf_10y_eur=12.80,
        volatility_3y=14.2,
        sharpe_ratio_3y=0.74,
        sources=["justetf", "morningstar"],
        data_quality_score=85.0,
    )


@pytest.fixture
def sample_search_criteria() -> SearchCriteria:
    """Crea criteri di ricerca di esempio."""
    return SearchCriteria(
        categories_morningstar=["Global Large-Cap Blend Equity"],
        currencies=["EUR"],
        distribution_filter=None,
        min_performance=50.0,
        performance_period="5y",
        instrument_types=[InstrumentType.ETF],
    )


@pytest.fixture
def multiple_source_records() -> List[SourceRecord]:
    """Crea lista di SourceRecord da fonti diverse per test merge."""
    return [
        SourceRecord(
            isin="IE00B4L5Y983",
            name="iShares Core MSCI World UCITS ETF",
            source="justetf",
            instrument_type=InstrumentType.ETF,
            currency="EUR",
            performance=PerformanceData(
                ytd=8.25,
                return_1y=15.30,
                return_3y=10.50,
                return_5y=11.64,
            ),
        ),
        SourceRecord(
            isin="IE00B4L5Y983",
            name="iShares Core MSCI World",
            source="morningstar",
            instrument_type=InstrumentType.ETF,
            currency="EUR",
            category_morningstar="Global Large-Cap Blend Equity",
            performance=PerformanceData(
                return_1y=15.28,
                return_3y=10.45,
            ),
        ),
        SourceRecord(
            isin="IE00B5BMR087",
            name="iShares Core S&P 500 UCITS ETF",
            source="justetf",
            instrument_type=InstrumentType.ETF,
            currency="USD",
            performance=PerformanceData(
                ytd=12.50,
                return_1y=20.30,
                return_5y=14.20,
            ),
        ),
    ]
