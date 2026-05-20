"""Unit tests for prediction strategies."""

import pytest

from billing_cost_prediction.strategies.exponential_smoothing import ExponentialSmoothingStrategy
from billing_cost_prediction.strategies.linear_trend import LinearTrendStrategy
from billing_cost_prediction.strategies.moving_average import MovingAverageStrategy
from billing_cost_prediction.strategies.seasonal import SeasonalStrategy
from billing_cost_prediction.types import BillingMonth, BillingRecord, CloudProvider


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
    def test_empty_records(self) -> None:
        strategy = MovingAverageStrategy(window_months=3)
        result = strategy.predict([], BillingMonth.from_string("2026-07"))
        assert result is None

    def test_flat_cost(self) -> None:
        records = _make_records([100.0, 100.0, 100.0])
        strategy = MovingAverageStrategy(window_months=3)
        result = strategy.predict(records, BillingMonth.from_string("2026-07"))
        assert result is not None
        assert result.predicted_cost == 100.0
        assert result.method == "moving_average"

    def test_increasing_cost(self) -> None:
        records = _make_records([50.0, 100.0, 150.0])
        strategy = MovingAverageStrategy(window_months=3)
        result = strategy.predict(records, BillingMonth.from_string("2026-07"))
        assert result is not None
        assert result.predicted_cost == 100.0

    def test_fewer_records_than_window(self) -> None:
        records = _make_records([100.0, 200.0])
        strategy = MovingAverageStrategy(window_months=5)
        result = strategy.predict(records, BillingMonth.from_string("2026-07"))
        assert result is not None
        assert result.predicted_cost == 150.0


class TestLinearTrendStrategy:
    def test_empty_records(self) -> None:
        strategy = LinearTrendStrategy()
        result = strategy.predict([], BillingMonth.from_string("2026-07"))
        assert result is None

    def test_too_few_records(self) -> None:
        records = _make_records([100.0, 200.0])
        strategy = LinearTrendStrategy(window_months=6)
        result = strategy.predict(records, BillingMonth.from_string("2026-07"))
        assert result is None

    def test_steady_growth(self) -> None:
        records = _make_records([100.0, 120.0, 140.0, 160.0, 180.0, 200.0])
        strategy = LinearTrendStrategy(window_months=6)
        result = strategy.predict(records, BillingMonth.from_string("2026-08"))
        assert result is not None
        assert result.predicted_cost > 200.0
        assert result.method == "linear_trend"

    def test_steady_decline(self) -> None:
        records = _make_records([200.0, 180.0, 160.0, 140.0, 120.0, 100.0])
        strategy = LinearTrendStrategy(window_months=6)
        result = strategy.predict(records, BillingMonth.from_string("2026-08"))
        assert result is not None
        assert result.predicted_cost < 100.0
        assert result.predicted_cost >= 0.0

    def test_predict_future_month(self) -> None:
        records = _make_records([100.0, 110.0, 120.0])
        strategy = LinearTrendStrategy(window_months=3)
        result = strategy.predict(records, BillingMonth.from_string("2026-10"))
        assert result is not None
        assert result.predicted_cost == pytest.approx(190.0, rel=0.01)


class TestSeasonalStrategy:
    def test_empty_records(self) -> None:
        strategy = SeasonalStrategy()
        result = strategy.predict([], BillingMonth.from_string("2026-07"))
        assert result is None

    def test_too_few_records(self) -> None:
        records = _make_records([100.0] * 6)
        strategy = SeasonalStrategy(window_months=12)
        result = strategy.predict(records, BillingMonth.from_string("2026-07"))
        assert result is None

    def test_seasonal_pattern(self) -> None:
        records = []
        month = BillingMonth.from_string("2025-01")
        for _ in range(12):
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


class TestExponentialSmoothingStrategy:
    def test_empty_records(self) -> None:
        strategy = ExponentialSmoothingStrategy()
        result = strategy.predict([], BillingMonth.from_string("2026-07"))
        assert result is None

    def test_flat_cost(self) -> None:
        records = _make_records([100.0, 100.0, 100.0])
        strategy = ExponentialSmoothingStrategy(alpha=0.3)
        result = strategy.predict(records, BillingMonth.from_string("2026-05"))
        assert result is not None
        assert result.predicted_cost == 100.0
        assert result.method == "exponential_smoothing"

    def test_increasing_trend(self) -> None:
        records = _make_records([100.0, 110.0, 120.0])
        strategy = ExponentialSmoothingStrategy(alpha=0.3)
        result = strategy.predict(records, BillingMonth.from_string("2026-05"))
        assert result is not None
        assert result.predicted_cost == pytest.approx(108.1, rel=0.01)

    def test_high_alpha_responds_faster(self) -> None:
        records = _make_records([100.0, 110.0, 120.0])
        strategy_low = ExponentialSmoothingStrategy(alpha=0.3)
        strategy_high = ExponentialSmoothingStrategy(alpha=0.8)
        result_low = strategy_low.predict(records, BillingMonth.from_string("2026-05"))
        result_high = strategy_high.predict(records, BillingMonth.from_string("2026-05"))
        assert result_low is not None and result_high is not None
        assert result_high.predicted_cost == pytest.approx(117.6, rel=0.01)
        assert result_high.predicted_cost > result_low.predicted_cost

    def test_invalid_alpha(self) -> None:
        with pytest.raises(ValueError):
            ExponentialSmoothingStrategy(alpha=0.0)
        with pytest.raises(ValueError):
            ExponentialSmoothingStrategy(alpha=1.0)
        with pytest.raises(ValueError):
            ExponentialSmoothingStrategy(alpha=1.5)


class TestStrategyValidation:
    def test_moving_average_invalid_window(self) -> None:
        with pytest.raises(ValueError):
            MovingAverageStrategy(window_months=0)

    def test_linear_trend_invalid_window(self) -> None:
        with pytest.raises(ValueError):
            LinearTrendStrategy(window_months=2)

    def test_seasonal_invalid_window(self) -> None:
        with pytest.raises(ValueError):
            SeasonalStrategy(window_months=11)

    def test_linear_trend_negative_cost_clamped(self) -> None:
        records = _make_records([100.0, 80.0, 60.0, 40.0, 20.0, 0.0])
        # With steep decline, the prediction for a far future month goes negative and should clamp
        strategy = LinearTrendStrategy(window_months=6)
        result = strategy.predict(records, BillingMonth.from_string("2027-01"))
        assert result is not None
        assert result.predicted_cost == 0.0

    def test_seasonal_with_gap_data(self) -> None:
        # Records for months 1,3,5,7,9,11 repeated twice (12 records, 24-month span)
        # Predicting for month 6: 6 not in window months -> no same_month_records
        records = []
        base = BillingMonth.from_string("2025-01")
        for i in range(12):
            m = base.months_ahead(i * 2)  # every other month
            records.append(
                BillingRecord(
                    resource_id="res-001",
                    cloud_provider=CloudProvider.AZURE,
                    billing_month=m,
                    cost=100.0,
                )
            )
        strategy = SeasonalStrategy(window_months=12)
        result = strategy.predict(records, BillingMonth.from_string("2026-02"))
        # Window covers Jan 2025 to Nov 2025 (every other month), Feb might not be in window
        # The window is last 12 records, which covers months: Jan,Mar,May,Jul,Sep,Nov + same next year
        # Feb is not in that set
        assert result is None

    def test_seasonal_all_months_zero(self) -> None:
        records = _make_records([0.0] * 12)
        strategy = SeasonalStrategy(window_months=12)
        result = strategy.predict(records, BillingMonth.from_string("2026-07"))
        assert result is not None
        assert result.predicted_cost == 0.0
