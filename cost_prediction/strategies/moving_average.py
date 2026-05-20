"""Moving average strategy — simple, robust, default choice."""

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

        sorted_records = sorted(records, key=lambda r: r.billing_month)
        window = sorted_records[-self.window_months :]

        if not window:
            return None

        avg_monthly_cost = sum(r.cost for r in window) / len(window)

        first = records[0]
        return PredictionResult(
            resource_id=first.resource_id,
            cloud_provider=first.cloud_provider,
            predict_month=target_month,
            predicted_cost=round(avg_monthly_cost, 4),
            currency=first.currency,
            method=self.name,
            baseline_months=[r.billing_month for r in window],
            baseline_cost=round(avg_monthly_cost, 4),
            product_name=first.product_name,
            resource_name=first.resource_name,
            resource_group=first.resource_group,
            service_category=first.service_category,
            pricing_model=first.pricing_model,
        )
