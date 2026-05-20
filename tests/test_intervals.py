"""Unit tests for prediction intervals."""

from cost_prediction.confidence import calculate_error_stats
from cost_prediction.engine import PredictionEngine
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


class TestCalculateErrorStats:
    def test_insufficient_data(self) -> None:
        records = _records(100, 200)
        mean_err, std_err = calculate_error_stats(records, MovingAverageStrategy().predict, test_window=3)
        assert mean_err == 0.0
        assert std_err == 0.0

    def test_perfect_predictions(self) -> None:
        records = _records(100, 100, 100, 100, 100)
        mean_err, std_err = calculate_error_stats(records, MovingAverageStrategy().predict, test_window=2)
        assert mean_err == 0.0
        assert std_err == 0.0


class TestPredictionIntervals:
    def test_intervals_set_on_results(self) -> None:
        records = _records(100, 110, 120, 130, 140, 150)
        engine = PredictionEngine()
        results = engine.predict(records, months=1)
        result = results[0].results[0]
        assert result.predicted_lower >= 0.0
        assert result.predicted_lower <= result.predicted_cost
        assert result.predicted_upper >= result.predicted_cost

    def test_intervals_tight_for_insufficient_data(self) -> None:
        records = _records(100, 200)
        engine = PredictionEngine()
        results = engine.predict(records, months=1)
        result = results[0].results[0]
        assert result.predicted_lower == result.predicted_cost
        assert result.predicted_upper == result.predicted_cost
