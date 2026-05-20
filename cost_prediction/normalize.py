"""Cost normalization — daily/monthly rate conversion for day-based billing.

Alibaba Cloud prepaid instances (包年包月) and some other billing models
charge by day but report by month. Monthly totals vary with calendar days
(31 vs 30 vs 28), making stable workloads look volatile.

Normalize to daily rates before prediction, then convert predictions back:

    records = to_daily_rates(records)       # ¥310 / 31 = ¥10
    results = engine.predict(records, 12)    # predict daily rates
    results = to_monthly_rates(results)      # ¥10 * 31 = ¥310
"""

import dataclasses

from cost_prediction.types import BillingMonth, BillingRecord, PredictionResult


def _days_in_month(month: BillingMonth) -> int:
    import calendar

    return calendar.monthrange(month.year, month.month)[1]


def to_daily_rates(records: list[BillingRecord]) -> list[BillingRecord]:
    """Convert monthly costs to daily rates.

    Each record's cost is divided by days in its billing month.
    Does not mutate input.
    """
    return [dataclasses.replace(r, cost=round(r.cost / _days_in_month(r.billing_month), 6)) for r in records]


def to_monthly_rates(results: list[PredictionResult]) -> list[PredictionResult]:
    """Convert daily-rate predictions back to monthly costs.

    Each prediction's cost is multiplied by days in the predicted month.
    Does not mutate input.
    """
    return [
        dataclasses.replace(
            r,
            predicted_cost=round(r.predicted_cost * _days_in_month(r.predict_month), 4),
            baseline_cost=round(r.baseline_cost * _days_in_month(r.predict_month), 4),
        )
        for r in results
    ]
