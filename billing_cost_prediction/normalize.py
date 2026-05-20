"""Cost normalization — time and volume adjustments for fair comparison.

Two normalization dimensions:

  Time (calendar effect):
    Alibaba prepaid ECS charges by day but bills by month. A stable ¥10/day
    workload looks volatile: Jan ¥310, Feb ¥280, Mar ¥310.
    → to_daily_rates / to_monthly_rates

  Volume (usage effect):
    Total cost = unit price × usage quantity. If usage doubled but unit
    price stayed flat, total cost looks like a spike.
    → to_unit_cost normalizes to cost per unit

Usage:

    # Normalize both dimensions before prediction
    records = to_daily_rates(records)            # eliminate calendar effect
    records = to_unit_cost(records)              # eliminate volume effect
    batches = engine.predict(records, 12)        # predict
    results = to_monthly_rates(batches[0].results)  # restore calendar
"""

import dataclasses

from billing_cost_prediction.types import BillingMonth, BillingRecord, PredictionResult


def _days_in_month(month: BillingMonth) -> int:
    import calendar

    return calendar.monthrange(month.year, month.month)[1]


def to_daily_rates(records: list[BillingRecord]) -> list[BillingRecord]:
    """Divide each record's cost by days in its billing month.

    Does not mutate input.
    """
    return [dataclasses.replace(r, cost=round(r.cost / _days_in_month(r.billing_month), 6)) for r in records]


def to_monthly_rates(results: list[PredictionResult]) -> list[PredictionResult]:
    """Multiply each prediction's cost by days in the predicted month.

    Does not mutate input.
    """
    return [
        dataclasses.replace(
            r,
            predicted_cost=round(r.predicted_cost * _days_in_month(r.predict_month), 4),
            baseline_cost=round(r.baseline_cost * _days_in_month(r.predict_month), 4),
            predicted_lower=round(r.predicted_lower * _days_in_month(r.predict_month), 4),
            predicted_upper=round(r.predicted_upper * _days_in_month(r.predict_month), 4),
        )
        for r in results
    ]


def to_unit_cost(records: list[BillingRecord]) -> list[BillingRecord]:
    """Divide each record's cost by its usage_quantity.

    Records with usage_quantity <= 0 keep their original cost.
    Always returns new objects (does not mutate input).
    """
    return [
        dataclasses.replace(r, cost=round(r.cost / r.usage_quantity, 6) if r.usage_quantity > 0 else r.cost)
        for r in records
    ]
