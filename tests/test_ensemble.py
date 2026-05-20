"""Unit tests for strategy ensemble."""

import pytest

from cost_prediction.ensemble import StrategyEnsemble
from cost_prediction.strategies.linear_trend import LinearTrendStrategy
from cost_prediction.strategies.moving_average import MovingAverageStrategy
from cost_prediction.types import BillingMonth, BillingRecord, CloudProvider


def _records(*costs: float) -> list[BillingRecord]:
    month = BillingMonth.from_string("2026-01")
    records = []
    for i, cost in enumerate(costs):
        m = month
        for _ in range(i):
            m = m.next_month()
        records.append(
            BillingRecord(
                resource_id="res-001",
                cloud_provider=CloudProvider.AZURE,
                billing_month=m,
                cost=cost,
            )
        )
    return records


class TestStrategyEnsemble:
    def test_empty_records(self) -> None:
        ensemble = StrategyEnsemble([MovingAverageStrategy(), LinearTrendStrategy()])
        assert ensemble.predict([], BillingMonth.from_string("2026-07")) is None

    def test_mean_method(self) -> None:
        recs = _records(100, 110, 120, 130, 140, 150)
        ensemble = StrategyEnsemble(
            [MovingAverageStrategy(window_months=3), LinearTrendStrategy(window_months=6)],
            method="mean",
        )
        result = ensemble.predict(recs, BillingMonth.from_string("2026-08"))
        assert result is not None
        assert result.method == "ensemble_mean"

    def test_weighted_method(self) -> None:
        recs = _records(100, 110, 120, 130, 140, 150)
        ensemble = StrategyEnsemble(
            [MovingAverageStrategy(window_months=3), LinearTrendStrategy(window_months=6)],
            method="weighted",
        )
        result = ensemble.predict(recs, BillingMonth.from_string("2026-08"))
        assert result is not None
        assert result.method == "ensemble_weighted"

    def test_median_method(self) -> None:
        recs = _records(100, 110, 120, 130, 140, 150)
        ensemble = StrategyEnsemble(
            [
                MovingAverageStrategy(window_months=3),
                LinearTrendStrategy(window_months=6),
                MovingAverageStrategy(window_months=6),
            ],
            method="median",
        )
        result = ensemble.predict(recs, BillingMonth.from_string("2026-08"))
        assert result is not None
        assert result.method == "ensemble_median"

    def test_single_strategy(self) -> None:
        recs = _records(100, 110, 120)
        ma = MovingAverageStrategy(window_months=3)
        ensemble = StrategyEnsemble([ma])
        result = ensemble.predict(recs, BillingMonth.from_string("2026-05"))
        solo = ma.predict(recs, BillingMonth.from_string("2026-05"))
        assert result is not None and solo is not None
        assert result.predicted_cost == solo.predicted_cost

    def test_invalid_method(self) -> None:
        with pytest.raises(ValueError):
            StrategyEnsemble([MovingAverageStrategy()], method="unknown")

    def test_empty_strategies(self) -> None:
        with pytest.raises(ValueError):
            StrategyEnsemble([])

    def test_partial_failure_fallback(self) -> None:
        # LinearTrend needs 3+ records in window, moving_average works with 1
        recs = _records(100, 200)  # only 2 records
        ensemble = StrategyEnsemble(
            [MovingAverageStrategy(window_months=3), LinearTrendStrategy(window_months=6)],
            method="mean",
        )
        result = ensemble.predict(recs, BillingMonth.from_string("2026-04"))
        assert result is not None
        assert result.method == "ensemble_mean"

    def test_metadata_inherited(self) -> None:
        recs = _records(100, 110, 120)
        ensemble = StrategyEnsemble([MovingAverageStrategy(), LinearTrendStrategy()])
        result = ensemble.predict(recs, BillingMonth.from_string("2026-05"))
        assert result is not None
        assert result.resource_id == "res-001"
        assert result.cloud_provider == CloudProvider.AZURE
