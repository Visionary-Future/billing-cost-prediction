"""Unit tests for prediction strategies."""

import pytest
from cost_prediction.strategies.linear_trend import LinearTrendStrategy
from cost_prediction.strategies.moving_average import MovingAverageStrategy
from cost_prediction.strategies.seasonal import SeasonalStrategy
from cost_prediction.types import BillingMonth, BillingRecord, CloudProvider


def _make_records(costs: list[float], base_month: str = "2026-01") -> list[BillingRecord]:
    month = BillingMonth.from_string(base_month)
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


class TestMovingAverageStrategy:
    def test_empty_records(self):
        strategy = MovingAverageStrategy(window_months=3)
        result = strategy.predict([], BillingMonth.from_string("2026-07"))
        assert result is None

    def test_flat_cost(self):
        records = _make_records([100.0, 100.0, 100.0])
        strategy = MovingAverageStrategy(window_months=3)
        result = strategy.predict(records, BillingMonth.from_string("2026-07"))
        assert result is not None
        assert result.predicted_cost == 100.0
        assert result.method == "moving_average"

    def test_increasing_cost(self):
        records = _make_records([50.0, 100.0, 150.0])
        strategy = MovingAverageStrategy(window_months=3)
        result = strategy.predict(records, BillingMonth.from_string("2026-07"))
        assert result is not None
        assert result.predicted_cost == 100.0

    def test_fewer_records_than_window(self):
        records = _make_records([100.0, 200.0])
        strategy = MovingAverageStrategy(window_months=5)
        result = strategy.predict(records, BillingMonth.from_string("2026-07"))
        assert result is not None
        assert result.predicted_cost == 150.0


class TestLinearTrendStrategy:
    def test_empty_records(self):
        strategy = LinearTrendStrategy()
        result = strategy.predict([], BillingMonth.from_string("2026-07"))
        assert result is None

    def test_too_few_records(self):
        records = _make_records([100.0, 200.0])
        strategy = LinearTrendStrategy(window_months=6)
        result = strategy.predict(records, BillingMonth.from_string("2026-07"))
        assert result is None

    def test_steady_growth(self):
        records = _make_records([100.0, 120.0, 140.0, 160.0, 180.0, 200.0])
        strategy = LinearTrendStrategy(window_months=6)
        result = strategy.predict(records, BillingMonth.from_string("2026-08"))
        assert result is not None
        assert result.predicted_cost > 200.0
        assert result.method == "linear_trend"

    def test_steady_decline(self):
        records = _make_records([200.0, 180.0, 160.0, 140.0, 120.0, 100.0])
        strategy = LinearTrendStrategy(window_months=6)
        result = strategy.predict(records, BillingMonth.from_string("2026-08"))
        assert result is not None
        assert result.predicted_cost < 100.0
        assert result.predicted_cost >= 0.0

    def test_predict_future_month(self):
        records = _make_records([100.0, 110.0, 120.0])
        strategy = LinearTrendStrategy(window_months=3)
        result = strategy.predict(records, BillingMonth.from_string("2026-10"))
        assert result is not None
        assert result.predicted_cost > 130.0


class TestSeasonalStrategy:
    def test_empty_records(self):
        strategy = SeasonalStrategy()
        result = strategy.predict([], BillingMonth.from_string("2026-07"))
        assert result is None

    def test_too_few_records(self):
        records = _make_records([100.0] * 6)
        strategy = SeasonalStrategy(window_months=12)
        result = strategy.predict(records, BillingMonth.from_string("2026-07"))
        assert result is None

    def test_seasonal_pattern(self):
        records = []
        month = BillingMonth.from_string("2025-01")
        for i in range(12):
            cost = 200.0 if month.month in (1, 7) else 100.0
            records.append(
                BillingRecord(
                    resource_id="res-001",
                    cloud_provider=CloudProvider.AZURE,
                    billing_month=month,
                    cost=cost,
                )
            )
            month = month.next_month()

        strategy = SeasonalStrategy(window_months=12)
        result = strategy.predict(records, BillingMonth.from_string("2026-01"))
        assert result is not None
        assert result.predicted_cost > 150.0
        assert result.method == "seasonal"
