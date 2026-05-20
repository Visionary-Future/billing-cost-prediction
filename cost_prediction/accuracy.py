"""Prediction accuracy tracking — MAPE and per-resource metrics."""

from collections import defaultdict

from cost_prediction.types import BillingRecord, PredictionResult


class MAPETracker:
    """Tracks Mean Absolute Percentage Error of predictions vs actuals.

    Records prediction-actual pairs over time and computes aggregate MAPE.
    """

    def __init__(self) -> None:
        self._abs_errors: list[float] = []
        self._by_resource: dict[str, list[float]] = defaultdict(list)
        self._count = 0

    @property
    def count(self) -> int:
        return self._count

    def record(
        self,
        predictions: list[PredictionResult],
        actuals: list[BillingRecord],
    ) -> None:
        if len(predictions) != len(actuals):
            raise ValueError(
                f"predictions and actuals must have same length, got {len(predictions)} and {len(actuals)}"
            )

        for pred, actual in zip(predictions, actuals, strict=False):
            if actual.cost == 0:
                continue
            ape = abs(pred.predicted_cost - actual.cost) / actual.cost * 100
            self._abs_errors.append(ape)
            self._by_resource[pred.resource_id].append(ape)
            self._count += 1

    def mape(self) -> float:
        """Overall MAPE across all recorded predictions."""
        if not self._abs_errors:
            return 0.0
        return round(sum(self._abs_errors) / len(self._abs_errors), 2)

    def mape_by_resource(self) -> dict[str, float]:
        """Per-resource MAPE."""
        return {rid: round(sum(errs) / len(errs), 2) for rid, errs in self._by_resource.items() if errs}

    def reset(self) -> None:
        self._abs_errors.clear()
        self._by_resource.clear()
        self._count = 0
