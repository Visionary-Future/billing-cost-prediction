"""Exponential smoothing strategy — weights recent data more heavily."""

from cost_prediction.types import BillingMonth, BillingRecord, PredictionResult


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

        sorted_records = sorted(records, key=lambda r: r.billing_month)
        costs = [r.cost for r in sorted_records]

        smoothed = costs[0]
        for cost in costs[1:]:
            smoothed = self.alpha * cost + (1 - self.alpha) * smoothed

        first = records[0]
        baseline_months = [r.billing_month for r in sorted_records]
        avg_cost = sum(costs) / len(costs)

        return PredictionResult(
            resource_id=first.resource_id,
            cloud_provider=first.cloud_provider,
            predict_month=target_month,
            predicted_cost=round(smoothed, 4),
            currency=first.currency,
            method=self.name,
            baseline_months=baseline_months,
            baseline_cost=round(avg_cost, 4),
            product_name=first.product_name,
            resource_name=first.resource_name,
            resource_group=first.resource_group,
            service_category=first.service_category,
            pricing_model=first.pricing_model,
        )
