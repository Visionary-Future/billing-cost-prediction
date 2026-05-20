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

def _days_in_month(month: BillingMonth) -> int:
    """Return the number of days in a given billing month."""
    import calendar

    return calendar.monthrange(month.year, month.month)[1]
