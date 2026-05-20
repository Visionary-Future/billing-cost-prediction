"""Prediction strategy protocol and common utilities."""

from typing import Protocol, runtime_checkable

from cost_prediction.types import BillingMonth, BillingRecord, PredictionResult


@runtime_checkable
class PredictionStrategy(Protocol):
    """Protocol for a cost prediction strategy.

    Each strategy takes a resource's historical billing records and
    predicts its cost for a single future month.
    """

    @property
    def name(self) -> str: ...

    def predict(
        self,
        records: list[BillingRecord],
        target_month: BillingMonth,
    ) -> PredictionResult | None:
        """Predict cost for a single resource in a target month.

        Args:
            records: Historical billing records for ONE resource, sorted by month.
            target_month: The month to predict for.

        Returns:
            PredictionResult if prediction is possible, None otherwise.
        """
        ...


def build_result(
    records: list[BillingRecord],
    target_month: BillingMonth,
    predicted_cost: float,
    method: str,
    baseline_months: list[BillingMonth],
    baseline_cost: float,
) -> PredictionResult:
    """Build a PredictionResult from a record set and computed values.

    Inherits metadata (resource_id, cloud_provider, product_name, etc.)
    from the first record.
    """
    first = records[0]
    return PredictionResult(
        resource_id=first.resource_id,
        cloud_provider=first.cloud_provider,
        predict_month=target_month,
        predicted_cost=round(predicted_cost, 4),
        currency=first.currency,
        method=method,
        baseline_months=baseline_months,
        baseline_cost=round(baseline_cost, 4),
        product_name=first.product_name,
        resource_name=first.resource_name,
        resource_group=first.resource_group,
        service_category=first.service_category,
        pricing_model=first.pricing_model,
    )
