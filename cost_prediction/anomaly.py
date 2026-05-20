"""Cost anomaly detection — pre-filter anomalous months before prediction."""

from collections import defaultdict

from cost_prediction.types import BillingRecord


class CostAnomalyDetector:
    """Detects anomalous billing months using IQR (Interquartile Range).

    Anomalies are detected per-resource. A month is flagged if its cost
    falls outside the fences:
        lower = Q1 - factor * IQR
        upper = Q3 + factor * IQR

    Default factor of 1.5 follows Tukey's fences convention.
    """

    def __init__(self, method: str = "iqr", factor: float = 1.5) -> None:
        if factor <= 0:
            raise ValueError(f"factor must be > 0, got {factor}")
        if method not in ("iqr",):
            raise ValueError(f"unknown method '{method}', expected 'iqr'")
        self.method = method
        self.factor = factor

    def detect(self, records: list[BillingRecord]) -> list[BillingRecord]:
        """Return anomalous records without modifying input."""
        if not records:
            return []

        anomalies: list[BillingRecord] = []
        for _resource_id, recs in self._group(records).items():
            anomalies.extend(self._detect_iqr(recs))
        return anomalies

    def filter(self, records: list[BillingRecord]) -> list[BillingRecord]:
        """Return clean records with anomalies removed."""
        anomalies = self.detect(records)
        if not anomalies:
            return list(records)
        anomaly_set = {id(r) for r in anomalies}
        return [r for r in records if id(r) not in anomaly_set]

    def _detect_iqr(self, records: list[BillingRecord]) -> list[BillingRecord]:
        if len(records) < 4:
            return []

        costs = sorted(r.cost for r in records)
        q1 = self._percentile(costs, 25)
        q3 = self._percentile(costs, 75)
        iqr = q3 - q1

        if iqr == 0:
            return []

        lower = q1 - self.factor * iqr
        upper = q3 + self.factor * iqr

        return [r for r in records if r.cost < lower or r.cost > upper]

    @staticmethod
    def _percentile(sorted_values: list[float], p: int) -> float:
        """Linear interpolation percentile. p in [0, 100]."""
        n = len(sorted_values)
        k = (p / 100) * (n - 1)
        f = int(k)
        c = k - f
        if f + 1 >= n:
            return sorted_values[f]
        return sorted_values[f] + c * (sorted_values[f + 1] - sorted_values[f])

    @staticmethod
    def _group(records: list[BillingRecord]) -> dict[str, list[BillingRecord]]:
        groups: dict[str, list[BillingRecord]] = defaultdict(list)
        for r in records:
            groups[r.resource_id].append(r)
        return dict(groups)
