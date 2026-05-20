"""Moving average strategy — simple, robust, default choice."""

from cost_prediction.strategies.base import build_result
from cost_prediction.types import BillingMonth, BillingRecord, PredictionResult


class MovingAverageStrategy:
    """Predicts future cost as the moving average of historical monthly costs.

    Suitable for stable workloads with no strong trend or seasonality.
    """

    name = "moving_average"

    def __init__(self, window_months: int = 3) -> None:
        if window_months < 1:
            raise ValueError("window_months must be >= 1")
        self.window_months = window_months

    def predict(
        self,
        records: list[BillingRecord],
        target_month: BillingMonth,
    ) -> PredictionResult | None:
        if not records:
            return None

        window = records[-self.window_months :]
        if not window:
            return None

        avg_monthly_cost = sum(r.cost for r in window) / len(window)

        return build_result(
            records,
            target_month,
            predicted_cost=avg_monthly_cost,
            method=self.name,
            baseline_months=[r.billing_month for r in window],
            baseline_cost=avg_monthly_cost,
        )
