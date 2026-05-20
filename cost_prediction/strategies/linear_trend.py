"""Linear trend strategy — fits a linear regression to historical costs and extrapolates."""

from cost_prediction.strategies.base import PredictionStrategy
from cost_prediction.types import BillingMonth, BillingRecord, PredictionResult


class LinearTrendStrategy:
    """Predicts future cost by fitting a linear trend to historical monthly costs.

    Suitable for workloads with consistent growth or decline patterns.
    """

    name = "linear_trend"

    def __init__(self, window_months: int = 6) -> None:
        if window_months < 3:
            raise ValueError("window_months must be >= 3 for meaningful trend")
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

        if len(window) < 3:
            return None

        costs = [r.cost for r in window]
        slope, intercept = self._fit_linear(costs)

        n = len(window)
        step = self._months_between(window[-1].billing_month, target_month)

        predicted = intercept + slope * (n + step - 1)

        if predicted < 0:
            predicted = 0.0

        last_window = [r.billing_month for r in window]
        avg_baseline = sum(costs) / len(costs)

        first = records[0]
        return PredictionResult(
            resource_id=first.resource_id,
            cloud_provider=first.cloud_provider,
            predict_month=target_month,
            predicted_cost=round(predicted, 4),
            currency=first.currency,
            method=self.name,
            baseline_months=last_window,
            baseline_cost=round(avg_baseline, 4),
            product_name=first.product_name,
            resource_name=first.resource_name,
            resource_group=first.resource_group,
            service_category=first.service_category,
            pricing_model=first.pricing_model,
        )

    @staticmethod
    def _fit_linear(y: list[float]) -> tuple[float, float]:
        """Simple linear regression: y = slope * x + intercept. Returns (slope, intercept)."""
        n = len(y)
        if n == 0:
            return 0.0, 0.0

        x_mean = (n - 1) / 2.0
        y_mean = sum(y) / n

        numerator = sum((i - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0, y_mean

        slope = numerator / denominator
        intercept = y_mean - slope * x_mean
        return slope, intercept

    @staticmethod
    def _months_between(a: BillingMonth, b: BillingMonth) -> int:
        return (b.year - a.year) * 12 + (b.month - a.month) + 1
