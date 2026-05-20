"""Unit tests for prediction accuracy tracking."""

import pytest

from cost_prediction.accuracy import MAPETracker
from cost_prediction.types import BillingMonth, BillingRecord, CloudProvider, PredictionResult


def _result(cost: float, resource_id: str = "res-001") -> PredictionResult:
    return PredictionResult(
        resource_id=resource_id,
        cloud_provider=CloudProvider.AZURE,
        predict_month=BillingMonth.from_string("2026-01"),
        predicted_cost=cost,
        method="test",
    )


def _record(cost: float, resource_id: str = "res-001") -> BillingRecord:
    return BillingRecord(
        resource_id=resource_id,
        cloud_provider=CloudProvider.AZURE,
        billing_month=BillingMonth.from_string("2026-01"),
        cost=cost,
    )


class TestMAPETracker:
    def test_empty(self) -> None:
        tracker = MAPETracker()
        assert tracker.mape() == 0.0
        assert tracker.mape_by_resource() == {}

    def test_perfect_prediction(self) -> None:
        tracker = MAPETracker()
        tracker.record([_result(100)], [_record(100)])
        assert tracker.mape() == 0.0

    def test_overestimate_mape(self) -> None:
        tracker = MAPETracker()
        tracker.record([_result(120)], [_record(100)])
        assert tracker.mape() == 20.0

    def test_underestimate_mape(self) -> None:
        tracker = MAPETracker()
        tracker.record([_result(80)], [_record(100)])
        assert tracker.mape() == 20.0

    def test_multiple_predictions(self) -> None:
        tracker = MAPETracker()
        tracker.record(
            [_result(110), _result(90), _result(200), _result(150)],
            [_record(100), _record(100), _record(200), _record(150)],
        )
        # |110-100|/100=10%, |90-100|/100=10%, |200-200|/200=0%, |150-150|/150=0%
        # MAPE = (10+10+0+0)/4 = 5%
        assert tracker.mape() == pytest.approx(5.0)

    def test_per_resource(self) -> None:
        tracker = MAPETracker()
        tracker.record(
            [_result(120, "res-a"), _result(200, "res-b")],
            [_record(100, "res-a"), _record(200, "res-b")],
        )
        by_res = tracker.mape_by_resource()
        assert by_res["res-a"] == 20.0
        assert by_res["res-b"] == 0.0

    def test_mismatched_lengths(self) -> None:
        tracker = MAPETracker()
        with pytest.raises(ValueError):
            tracker.record([_result(100)], [])

    def test_count(self) -> None:
        tracker = MAPETracker()
        tracker.record([_result(100)], [_record(100)])
        tracker.record([_result(110), _result(90)], [_record(100), _record(100)])
        assert tracker.count == 3

    def test_actual_zero(self) -> None:
        tracker = MAPETracker()
        tracker.record([_result(10)], [_record(0)])
        # Actual is 0, predicted is 10: MAPE is undefined, skip
        assert tracker.mape() == 0.0
        assert tracker.count == 0

    def test_reset(self) -> None:
        tracker = MAPETracker()
        tracker.record([_result(120)], [_record(100)])
        tracker.reset()
        assert tracker.mape() == 0.0
        assert tracker.count == 0
