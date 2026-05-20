"""Confidence scoring based on historical prediction accuracy."""

from collections.abc import Callable

from cost_prediction.types import BillingMonth, BillingRecord, PredictionResult


def calculate_confidence_from_history(
    records: list[BillingRecord],
    prediction_fn: Callable[[list[BillingRecord], BillingMonth], PredictionResult | None],
    test_window: int = 3,
) -> float:
    """Calculate confidence by back-testing the prediction function against known data.

    For each of the last `test_window` months where we have actual cost data,
    run the prediction function using data from before that month, then compare
    predicted vs actual.

    Returns a confidence score between 0.0 and 1.0.
    """
    if len(records) < test_window + 2:
        return 0.5

    sorted_records = sorted(records, key=lambda r: r.billing_month)

    errors: list[float] = []
    for i in range(test_window, 0, -1):
        split_at = len(sorted_records) - i
        training = sorted_records[:split_at]
        actual = sorted_records[split_at:]

        if not actual:
            continue

        actual_month_data = [r for r in actual if r.billing_month == actual[0].billing_month]
        if not actual_month_data:
            continue

        result = prediction_fn(training, actual[0].billing_month)
        if result is None:
            continue

        actual_cost = sum(r.cost for r in actual_month_data)
        if actual_cost > 0:
            error_rate = abs(result.predicted_cost - actual_cost) / max(actual_cost, result.predicted_cost)
        elif result.predicted_cost == 0:
            continue
        else:
            error_rate = 1.0

        errors.append(error_rate)

    if not errors:
        return 0.5

    mean_error = sum(errors) / len(errors)
    confidence = 1.0 - min(mean_error, 1.0)
    return round(max(0.0, min(confidence, 1.0)), 4)


def calculate_error_stats(
    records: list[BillingRecord],
    prediction_fn: Callable[[list[BillingRecord], BillingMonth], PredictionResult | None],
    test_window: int = 3,
) -> tuple[float, float]:
    """Back-test and return (mean_absolute_error, std_error) in cost units.

    Uses the same back-testing logic as calculate_confidence_from_history
    but returns raw error statistics for prediction interval construction.
    """
    if len(records) < test_window + 2:
        return (0.0, 0.0)

    sorted_records = sorted(records, key=lambda r: r.billing_month)

    abs_errors: list[float] = []
    for i in range(test_window, 0, -1):
        split_at = len(sorted_records) - i
        training = sorted_records[:split_at]
        actual = sorted_records[split_at:]

        if not actual:
            continue

        actual_month_data = [r for r in actual if r.billing_month == actual[0].billing_month]
        if not actual_month_data:
            continue

        result = prediction_fn(training, actual[0].billing_month)
        if result is None:
            continue

        actual_cost = sum(r.cost for r in actual_month_data)
        abs_errors.append(abs(result.predicted_cost - actual_cost))

    if not abs_errors:
        return (0.0, 0.0)

    mean_err = sum(abs_errors) / len(abs_errors)
    if len(abs_errors) < 2:
        return (mean_err, 0.0)

    variance = sum((e - mean_err) ** 2 for e in abs_errors) / (len(abs_errors) - 1)
    return (round(mean_err, 4), round(variance**0.5, 4))


def default_confidence(data_points: int) -> float:
    """Fallback confidence based purely on sample size."""
    if data_points >= 12:
        return 0.85
    elif data_points >= 6:
        return 0.70
    elif data_points >= 3:
        return 0.55
    else:
        return 0.40
