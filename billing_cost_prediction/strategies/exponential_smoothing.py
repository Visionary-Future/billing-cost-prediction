"""Exponential smoothing strategy — weights recent data more heavily."""

from billing_cost_prediction.strategies.base import build_result
from billing_cost_prediction.types import BillingMonth, BillingRecord, PredictionResult


class ExponentialSmoothingStrategy:
    """Predicts future cost using single exponential smoothing.

    Assigns exponentially decreasing weights to older observations:
        S_t = alpha * Y_t + (1 - alpha) * S_{t-1}

    Suitable for data with moderate noise where recent observations
    are more indicative of future costs.
    """

    name = "exponential_smoothing"

    def __init__(self, alpha: float = 0.3) -> None:
        if not (0.0 < alpha < 1.0):
            raise ValueError(f"alpha must be in (0, 1), got {alpha}")
        self.alpha = alpha

    def predict(
        self,
        records: list[BillingRecord],
        target_month: BillingMonth,
    ) -> PredictionResult | None:
        if not records:
            return None

        costs = [r.cost for r in records]

        smoothed = costs[0]
        for cost in costs[1:]:
            smoothed = self.alpha * cost + (1 - self.alpha) * smoothed

        avg_cost = sum(costs) / len(costs)

        return build_result(
            records,
            target_month,
            predicted_cost=smoothed,
            method=self.name,
            baseline_months=[r.billing_month for r in records],
            baseline_cost=avg_cost,
        )
