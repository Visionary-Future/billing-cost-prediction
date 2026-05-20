"""Integration tests for the prediction engine."""

from billing_cost_prediction.engine import PredictionEngine
from billing_cost_prediction.types import BillingMonth, BillingRecord, CloudProvider


def _make_records(
    resource_id: str = "res-001",
    provider: CloudProvider = CloudProvider.AZURE,
    costs: list[float] | None = None,
    base_month: str = "2026-01",
) -> list[BillingRecord]:
    if costs is None:
        costs = [100.0, 110.0, 120.0]
    month = BillingMonth.from_string(base_month)
    records = []
    for i, cost in enumerate(costs):
        m = month
        for _ in range(i):
            m = m.next_month()
        records.append(
            BillingRecord(
                resource_id=resource_id,
                cloud_provider=provider,
                billing_month=m,
                cost=cost,
            )
        )
    return records


class TestPredictionEngine:
    def test_empty_records(self) -> None:
        engine = PredictionEngine()
        results = engine.predict([], months=12)
        assert results == []

    def test_single_resource(self) -> None:
        records = _make_records()
        engine = PredictionEngine()
        results = engine.predict(records, months=3)
        assert len(results) == 1
        batch = results[0]
        assert batch.provider == CloudProvider.AZURE
        assert batch.total_resources == 1
        assert len(batch.results) == 3  # 3 months

    def test_multi_resource(self) -> None:
        records = _make_records(resource_id="res-001") + _make_records(resource_id="res-002")
        engine = PredictionEngine()
        results = engine.predict(records, months=2)
        assert len(results) == 1
        batch = results[0]
        assert batch.total_resources == 2
        assert len(batch.results) == 4  # 2 resources x 2 months

    def test_multi_provider(self) -> None:
        records = _make_records(provider=CloudProvider.AZURE, costs=[100.0, 110.0, 120.0])
        records += _make_records(provider=CloudProvider.ALIBABA, costs=[50.0, 60.0, 70.0])
        engine = PredictionEngine()
        results = engine.predict(records, months=1)
        assert len(results) == 2
        providers = {r.provider for r in results}
        assert CloudProvider.AZURE in providers
        assert CloudProvider.ALIBABA in providers

    def test_explicit_strategy(self) -> None:
        records = _make_records()
        engine = PredictionEngine()
        results = engine.predict(records, months=1, strategy="linear_trend")
        assert len(results) == 1
        assert results[0].results[0].method == "linear_trend"

    def test_auto_strategy_selection(self) -> None:
        engine = PredictionEngine()
        single = _make_records(costs=[100.0])
        assert engine.predict(single, months=1)[0].results[0].method == "moving_average"
        couple = _make_records(costs=[100.0, 200.0])
        assert engine.predict(couple, months=1)[0].results[0].method == "exponential_smoothing"

    def test_confidence_is_set(self) -> None:
        records = _make_records(costs=[100.0, 110.0, 120.0, 130.0, 140.0, 150.0])
        engine = PredictionEngine()
        results = engine.predict(records, months=1)
        assert len(results) == 1
        assert 0.0 <= results[0].results[0].confidence <= 1.0

    def test_custom_start_month(self) -> None:
        records = _make_records(costs=[100.0, 110.0, 120.0], base_month="2026-01")
        engine = PredictionEngine()
        results = engine.predict(records, months=1, start_month=BillingMonth.from_string("2026-06"))
        assert len(results) == 1
        assert results[0].results[0].predict_month == BillingMonth.from_string("2026-06")

    def test_auto_picks_seasonal_for_12plus(self) -> None:
        records = _make_records(costs=list(range(1, 13)))
        engine = PredictionEngine()
        results = engine.predict(records, months=1)
        assert results[0].results[0].method == "seasonal"

    def test_multi_resource_with_different_history_lengths(self) -> None:
        res_a = _make_records(resource_id="res-a", costs=[100.0] * 12)
        res_b = _make_records(resource_id="res-b", costs=[200.0, 300.0])
        engine = PredictionEngine()
        results = engine.predict(res_a + res_b, months=1)
        assert len(results) == 1
        methods = {r.method for r in results[0].results}
        assert "seasonal" in methods
        assert "exponential_smoothing" in methods

    def test_nonexistent_strategy(self) -> None:
        records = _make_records()
        engine = PredictionEngine()
        results = engine.predict(records, months=1, strategy="nonexistent")
        assert len(results) == 1
        assert len(results[0].errors) == 1
        assert len(results[0].results) == 0
