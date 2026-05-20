"""Strategy ensemble — multi-strategy voting for improved predictions."""

from statistics import median as _median

from cost_prediction.strategies.base import PredictionStrategy, build_result
from cost_prediction.types import BillingMonth, BillingRecord, PredictionResult


class StrategyEnsemble:
    """Combines multiple strategies into a single meta-strategy.

    Supports three aggregation methods:
      - mean:  simple average of all strategy predictions
      - median: median of all strategy predictions (robust to outliers)
      - weighted: weighted by inverse baseline deviation (strategies closer to group mean weighted higher)

    The ensemble implements the PredictionStrategy Protocol, so it can
    be used anywhere a single strategy is expected.
    """

    name = "ensemble"

    def __init__(
        self,
        strategies: list[PredictionStrategy],
        method: str = "mean",
    ) -> None:
        if not strategies:
            raise ValueError("at least one strategy is required")
        if method not in ("mean", "median", "weighted"):
            raise ValueError(f"unknown method '{method}', expected 'mean', 'median', or 'weighted'")
        self.strategies = strategies
        self.method = method

    def predict(
        self,
        records: list[BillingRecord],
        target_month: BillingMonth,
    ) -> PredictionResult | None:
        if not records:
            return None

        results: list[PredictionResult] = []
        for strategy in self.strategies:
            r = strategy.predict(records, target_month)
            if r is not None:
                results.append(r)

        if not results:
            return None

        if self.method == "median":
            predicted = _median(r.predicted_cost for r in results)
        elif self.method == "weighted":
            predicted = self._weighted_average(results)
        else:
            predicted = sum(r.predicted_cost for r in results) / len(results)

        avg_baseline = sum(r.baseline_cost for r in results) / len(results)

        return build_result(
            records,
            target_month,
            predicted_cost=predicted,
            method=f"ensemble_{self.method}",
            baseline_months=results[0].baseline_months,
            baseline_cost=avg_baseline,
        )

    @staticmethod
    def _weighted_average(results: list[PredictionResult]) -> float:
        if len(results) == 1:
            return results[0].predicted_cost
        # Use inverse baseline variance as proxy for precision
        baselines = [r.baseline_cost for r in results]
        mean_b = sum(baselines) / len(baselines)
        if mean_b == 0:
            return sum(r.predicted_cost for r in results) / len(results)
        # Weight by inverse relative deviation from mean baseline
        devs = [abs(b - mean_b) / mean_b for b in baselines]
        weights = [1.0 / (d + 0.01) for d in devs]
        total_w = sum(weights)
        return sum(r.predicted_cost * w for r, w in zip(results, weights, strict=False)) / total_w
