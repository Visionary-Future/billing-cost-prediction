"""Unit tests for confidence scoring."""

from cost_prediction.confidence import calculate_confidence_from_history, default_confidence
from cost_prediction.strategies.moving_average import MovingAverageStrategy
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


class TestDefaultConfidence:
    def test_12plus_data_points(self) -> None:
        assert default_confidence(12) == 0.85

    def test_6_to_11_data_points(self) -> None:
        assert default_confidence(6) == 0.70

    def test_3_to_5_data_points(self) -> None:
        assert default_confidence(3) == 0.55

    def test_less_than_3_data_points(self) -> None:
        assert default_confidence(2) == 0.40


class TestCalculateConfidence:
    def test_not_enough_data_returns_neutral(self) -> None:
        records = _make_records([100.0] * 4)
        strategy = MovingAverageStrategy()
        result = calculate_confidence_from_history(records, strategy.predict, test_window=3)
        # len(records)=4, test_window=3, 4 < 3+2=5 → returns 0.5
        assert result == 0.5

    def test_basic_backtest(self) -> None:
        records = _make_records([100.0, 100.0, 100.0, 100.0, 100.0])
        strategy = MovingAverageStrategy()
        result = calculate_confidence_from_history(records, strategy.predict, test_window=2)
        assert 0.0 <= result <= 1.0

    def test_no_errors_returns_neutral(self) -> None:
        # With insufficient data for any back-test, returns 0.5
        records = _make_records([100.0, 100.0])
        strategy = MovingAverageStrategy()
        result = calculate_confidence_from_history(records, strategy.predict, test_window=1)
        # len(records)=2, test_window=1, 2 < 1+2=3 → returns 0.5
        assert result == 0.5

    def test_actual_zero_predicted_zero_skipped(self) -> None:
        # Records where actual and predicted are both 0 should be skipped
        records = _make_records([0.0, 0.0, 0.0, 0.0, 0.0])
        strategy = MovingAverageStrategy()
        result = calculate_confidence_from_history(records, strategy.predict, test_window=2)
        # All predictions are 0, all actuals are 0 → all skipped → 0.5 neutral
        assert result == 0.5
