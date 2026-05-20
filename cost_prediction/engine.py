"""Prediction engine — orchestrates strategy selection and batch prediction."""

import dataclasses
import logging
from collections import defaultdict

from cost_prediction.confidence import calculate_confidence_from_history, calculate_error_stats, default_confidence
from cost_prediction.strategies.base import PredictionStrategy
from cost_prediction.strategies.exponential_smoothing import ExponentialSmoothingStrategy
from cost_prediction.strategies.linear_trend import LinearTrendStrategy
from cost_prediction.strategies.moving_average import MovingAverageStrategy
from cost_prediction.strategies.seasonal import SeasonalStrategy
from cost_prediction.types import (
    BillingMonth,
    BillingRecord,
    CloudProvider,
    PredictionBatchResult,
    PredictionResult,
)

logger = logging.getLogger(__name__)

DEFAULT_STRATEGIES: dict[str, PredictionStrategy] = {
    "exponential_smoothing": ExponentialSmoothingStrategy(alpha=0.3),
    "moving_average": MovingAverageStrategy(window_months=3),
    "linear_trend": LinearTrendStrategy(window_months=6),
    "seasonal": SeasonalStrategy(window_months=12),
}


class PredictionEngine:
    """Cloud cost prediction engine — strategy-based, framework-agnostic.

    Usage:
        engine = PredictionEngine()
        results = engine.predict(records, months=12)
    """

    def __init__(
        self,
        strategies: dict[str, PredictionStrategy] | None = None,
    ) -> None:
        self.strategies = strategies or DEFAULT_STRATEGIES

    def predict(
        self,
        records: list[BillingRecord],
        months: int = 12,
        strategy: str = "auto",
        start_month: BillingMonth | None = None,
    ) -> list[PredictionBatchResult]:
        """Predict future costs for a set of billing records.

        Args:
            records: Historical billing records, can span multiple resources.
            months: Number of future months to predict.
            strategy: Strategy name. "auto" picks based on data characteristics.
            start_month: Base month for prediction window. Defaults to the
                         month after the latest record.

        Returns:
            One PredictionBatchResult per cloud provider.
        """
        if not records:
            return []

        records_by_provider = self._group_by_provider(records)
        results: list[PredictionBatchResult] = []

        for provider, provider_records in records_by_provider.items():
            batch = self._predict_for_provider(
                provider_records,
                provider,
                months,
                strategy,
                start_month,
            )
            if batch:
                results.append(batch)

        return results

    def _predict_for_provider(
        self,
        records: list[BillingRecord],
        provider: CloudProvider,
        months: int,
        fallback_strategy: str,
        start_month: BillingMonth | None,
    ) -> PredictionBatchResult | None:
        records_by_resource = self._group_by_resource(records)

        if not records_by_resource:
            return None

        if start_month is None:
            all_months = sorted({r.billing_month for r in records})
            start_month = all_months[-1].next_month() if all_months else BillingMonth.from_date(2026, 1)

        all_results: list[PredictionResult] = []
        errors: list[str] = []
        total_predicted = 0.0

        for resource_id, resource_records in records_by_resource.items():
            strategy_name = self._resolve_strategy(fallback_strategy, resource_records)
            strategy = self.strategies.get(strategy_name)

            if strategy is None:
                errors.append(f"{resource_id}: no strategy found for '{strategy_name}'")
                continue

            confidence = self._compute_confidence(resource_records, strategy)
            lower, upper = self._compute_bounds(resource_records, strategy)

            target = start_month
            for _ in range(months):
                try:
                    strategy_result = strategy.predict(resource_records, target)
                    if strategy_result is not None:
                        predicted = strategy_result.predicted_cost
                        result = dataclasses.replace(
                            strategy_result,
                            confidence=confidence,
                            predicted_lower=round(max(0.0, predicted + lower), 4),
                            predicted_upper=round(max(0.0, predicted + upper), 4),
                        )
                        all_results.append(result)
                        total_predicted += result.predicted_cost
                except Exception as exc:
                    errors.append(f"{resource_id}/{target}: {exc}")
                target = target.next_month()

        return PredictionBatchResult(
            results=all_results,
            provider=provider,
            total_resources=len(records_by_resource),
            total_predicted=round(total_predicted, 2),
            errors=errors,
        )

    def _resolve_strategy(
        self,
        strategy_name: str,
        sample_records: list[BillingRecord],
    ) -> str:
        """Resolve strategy name. If 'auto', pick based on data characteristics."""
        if strategy_name != "auto":
            return strategy_name

        n = len(sample_records)
        if n >= 12:
            return "seasonal"
        if n >= 6:
            return "linear_trend"
        if n >= 2:
            return "exponential_smoothing"
        return "moving_average"

    def _compute_confidence(
        self,
        records: list[BillingRecord],
        strategy: PredictionStrategy,
    ) -> float:
        if len(records) <= 2:
            return default_confidence(len(records))
        test_window = max(3, min(12, len(records) // 4))
        try:
            return calculate_confidence_from_history(
                records,
                strategy.predict,
                test_window=test_window,
            )
        except Exception:
            return default_confidence(len(records))

    def _compute_bounds(
        self,
        records: list[BillingRecord],
        strategy: PredictionStrategy,
    ) -> tuple[float, float]:
        """Return (offset_to_lower, offset_to_upper) for 95% prediction interval.

        Uses back-test error standard deviation. Zero offset when
        insufficient data for error estimation.
        """
        if len(records) <= 2:
            return (0.0, 0.0)
        test_window = max(3, min(12, len(records) // 4))
        try:
            _mean_err, std_err = calculate_error_stats(
                records,
                strategy.predict,
                test_window=test_window,
            )
            if std_err == 0.0:
                return (0.0, 0.0)
            # 95% interval: ±1.96σ
            margin = round(1.96 * std_err, 4)
            return (-margin, margin)
        except Exception:
            return (0.0, 0.0)

    @staticmethod
    def _group_by_provider(
        records: list[BillingRecord],
    ) -> dict[CloudProvider, list[BillingRecord]]:
        groups: dict[CloudProvider, list[BillingRecord]] = defaultdict(list)
        for r in records:
            groups[r.cloud_provider].append(r)
        return dict(groups)

    @staticmethod
    def _group_by_resource(
        records: list[BillingRecord],
    ) -> dict[str, list[BillingRecord]]:
        groups: dict[str, list[BillingRecord]] = defaultdict(list)
        for r in records:
            groups[r.resource_id].append(r)
        return {rid: sorted(recs, key=lambda r: r.billing_month) for rid, recs in groups.items()}
