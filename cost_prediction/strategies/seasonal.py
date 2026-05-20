"""Seasonal strategy — detects year-over-year patterns and applies seasonal factors."""

from cost_prediction.types import BillingMonth, BillingRecord, PredictionResult


class SeasonalStrategy:
    """Predicts future cost by applying year-over-year seasonal factors.

    Suitable for workloads with recurring annual patterns (e.g. retail peaks).
    Requires at least 12 months of history.
    """

    name = "seasonal"

    def __init__(self, window_months: int = 12) -> None:
        if window_months < 12:
            raise ValueError("window_months must be >= 12 for seasonal detection")
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

        if len(window) < 12:
            return None

        target_month_num = target_month.month

        same_month_records = [r for r in window if r.billing_month.month == target_month_num]
        if not same_month_records:
            return None

        seasonal_avg = sum(r.cost for r in same_month_records) / len(same_month_records)

        all_months_avg = sum(r.cost for r in window) / len(window)
        seasonal_factor = 1.0 if all_months_avg <= 0 else seasonal_avg / all_months_avg

        recent_avg = sum(r.cost for r in window[-3:]) / 3
        predicted = recent_avg * seasonal_factor

        first = records[0]
        return PredictionResult(
            resource_id=first.resource_id,
            cloud_provider=first.cloud_provider,
            predict_month=target_month,
            predicted_cost=round(predicted, 4),
            currency=first.currency,
            method=self.name,
            baseline_months=[r.billing_month for r in window],
            baseline_cost=round(all_months_avg, 4),
            product_name=first.product_name,
            resource_name=first.resource_name,
            resource_group=first.resource_group,
            service_category=first.service_category,
            pricing_model=first.pricing_model,
        )
