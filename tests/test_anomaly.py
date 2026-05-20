"""Unit tests for cost anomaly detection."""

import pytest

from billing_cost_prediction.anomaly import CostAnomalyDetector
from billing_cost_prediction.types import BillingMonth, BillingRecord, CloudProvider


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


class TestCostAnomalyDetector:
    def test_empty_records(self) -> None:
        detector = CostAnomalyDetector()
        assert detector.detect([]) == []
        assert detector.filter([]) == []

    def test_too_few_records(self) -> None:
        detector = CostAnomalyDetector()
        recs = _records(100.0, 200.0)
        assert detector.detect(recs) == []
        assert detector.filter(recs) == recs

    def test_no_anomalies_stable_costs(self) -> None:
        detector = CostAnomalyDetector()
        recs = _records(100, 105, 102, 108, 103, 106, 104, 107)
        assert detector.detect(recs) == []
        assert detector.filter(recs) == recs

    def test_detect_spike(self) -> None:
        detector = CostAnomalyDetector()
        recs = _records(100, 105, 102, 108, 103, 500, 104, 107)
        anomalies = detector.detect(recs)
        assert len(anomalies) == 1
        assert anomalies[0].cost == 500.0

    def test_detect_drop(self) -> None:
        detector = CostAnomalyDetector()
        recs = _records(100, 105, 102, 108, 103, 10, 104, 107)
        anomalies = detector.detect(recs)
        assert len(anomalies) == 1
        assert anomalies[0].cost == 10.0

    def test_filter_removes_anomalies(self) -> None:
        detector = CostAnomalyDetector()
        recs = _records(100, 105, 102, 108, 103, 500, 104, 107)
        clean = detector.filter(recs)
        assert len(clean) == 7
        assert all(r.cost != 500.0 for r in clean)

    def test_custom_factor(self) -> None:
        detector_strict = CostAnomalyDetector(factor=1.0)
        detector_loose = CostAnomalyDetector(factor=3.0)
        recs = _records(100, 102, 104, 103, 105, 112, 101, 106)
        assert len(detector_strict.detect(recs)) == 1
        assert len(detector_loose.detect(recs)) == 0

    def test_invalid_factor(self) -> None:
        with pytest.raises(ValueError):
            CostAnomalyDetector(factor=0)
        with pytest.raises(ValueError):
            CostAnomalyDetector(factor=-1)

    def test_invalid_method(self) -> None:
        with pytest.raises(ValueError):
            CostAnomalyDetector(method="unknown")

    def test_multi_resource_independent(self) -> None:
        detector = CostAnomalyDetector()
        base = BillingMonth.from_string("2026-01")
        res_a = [
            BillingRecord(
                resource_id="res-a", cloud_provider=CloudProvider.AZURE, billing_month=base.months_ahead(i), cost=c
            )
            for i, c in enumerate([100, 102, 105, 500, 103, 104])
        ]
        res_b = [
            BillingRecord(
                resource_id="res-b", cloud_provider=CloudProvider.AZURE, billing_month=base.months_ahead(i), cost=c
            )
            for i, c in enumerate([100, 102, 105, 108, 103, 104])
        ]
        all_recs = res_a + res_b
        anomalies = detector.detect(all_recs)
        assert len(anomalies) == 1
        assert anomalies[0].resource_id == "res-a"
