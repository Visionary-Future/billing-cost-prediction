"""Unit tests for cost normalization."""

from cost_prediction.normalize import to_daily_rates, to_monthly_rates, to_unit_cost
from cost_prediction.types import BillingMonth, BillingRecord, CloudProvider, PredictionResult


def _record(month_str: str, cost: float, qty: float = 0.0) -> BillingRecord:
    return BillingRecord(
        resource_id="res-001",
        cloud_provider=CloudProvider.ALIBABA,
        billing_month=BillingMonth.from_string(month_str),
        cost=cost,
        usage_quantity=qty,
    )


def _result(month_str: str, cost: float, baseline_cost: float = 0.0) -> PredictionResult:
    return PredictionResult(
        resource_id="res-001",
        cloud_provider=CloudProvider.ALIBABA,
        predict_month=BillingMonth.from_string(month_str),
        predicted_cost=cost,
        baseline_cost=baseline_cost,
        method="test",
    )


class TestToDailyRates:
    def test_31_day_month(self) -> None:
        recs = [_record("2025-01", 310.0)]
        result = to_daily_rates(recs)
        assert result[0].cost == 10.0

    def test_28_day_month(self) -> None:
        recs = [_record("2025-02", 280.0)]
        result = to_daily_rates(recs)
        assert result[0].cost == 10.0

    def test_30_day_month(self) -> None:
        recs = [_record("2025-04", 300.0)]
        result = to_daily_rates(recs)
        assert result[0].cost == 10.0

    def test_does_not_mutate_input(self) -> None:
        recs = [_record("2025-01", 310.0)]
        to_daily_rates(recs)
        assert recs[0].cost == 310.0

    def test_preserves_metadata(self) -> None:
        recs = [_record("2025-01", 310.0)]
        result = to_daily_rates(recs)[0]
        assert result.resource_id == "res-001"
        assert result.cloud_provider == CloudProvider.ALIBABA

    def test_prepaid_ecs_full_year(self) -> None:
        """ECS prepaid: ¥3650/year = ¥10/day, consistent daily rate."""
        recs = [
            _record("2025-01", 310),
            _record("2025-02", 280),
            _record("2025-03", 310),
            _record("2025-04", 300),
            _record("2025-05", 310),
            _record("2025-06", 300),
            _record("2025-07", 310),
            _record("2025-08", 310),
            _record("2025-09", 300),
            _record("2025-10", 310),
            _record("2025-11", 300),
            _record("2025-12", 310),
        ]
        daily = to_daily_rates(recs)
        for r in daily:
            assert r.cost == 10.0


class TestToMonthlyRates:
    def test_january_prediction(self) -> None:
        results = [_result("2026-01", 10.0, baseline_cost=10.0)]
        monthly = to_monthly_rates(results)
        assert monthly[0].predicted_cost == 310.0
        assert monthly[0].baseline_cost == 310.0

    def test_february_prediction(self) -> None:
        results = [_result("2026-02", 10.0)]
        monthly = to_monthly_rates(results)
        assert monthly[0].predicted_cost == 280.0

    def test_does_not_mutate_input(self) -> None:
        results = [_result("2026-01", 10.0)]
        to_monthly_rates(results)
        assert results[0].predicted_cost == 10.0

    def test_roundtrip(self) -> None:
        """Daily conversion → monthly prediction gives correct calendar result."""
        recs = [
            _record("2025-01", 310),
            _record("2025-02", 280),
            _record("2025-03", 310),
        ]
        daily = to_daily_rates(recs)
        assert all(r.cost == 10.0 for r in daily)
        # Simulate flat daily rate prediction → 30-day April = ¥300
        results = [_result("2025-04", 10.0)]
        monthly = to_monthly_rates(results)
        assert monthly[0].predicted_cost == 300.0  # April has 30 days


class TestToUnitCost:
    def test_normalizes_by_quantity(self) -> None:
        recs = [_record("2025-01", 1000.0, qty=100)]
        result = to_unit_cost(recs)
        assert result[0].cost == 10.0

    def test_zero_quantity_passed_through(self) -> None:
        recs = [_record("2025-01", 100.0, qty=0.0)]
        result = to_unit_cost(recs)
        assert result[0].cost == 100.0

    def test_does_not_mutate_input(self) -> None:
        recs = [_record("2025-01", 1000.0, qty=100)]
        to_unit_cost(recs)
        assert recs[0].cost == 1000.0

    def test_usage_doubled_total_flat(self) -> None:
        """Cost doubles but usage doubles → unit cost stays flat."""
        recs = [
            _record("2025-01", 500.0, qty=50),
            _record("2025-02", 1000.0, qty=100),
        ]
        unit = to_unit_cost(recs)
        assert unit[0].cost == 10.0
        assert unit[1].cost == 10.0
