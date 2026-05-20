"""Prediction engine — orchestrates strategy selection and batch prediction."""

import dataclasses
import logging
from collections import defaultdict
from typing import Optional

from cost_prediction.confidence import calculate_confidence_from_history, default_confidence
from cost_prediction.strategies.base import PredictionStrategy
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
        auto_strategy: bool = True,
    ) -> None:
        self.strategies = strategies or DEFAULT_STRATEGIES
        self.auto_strategy = auto_strategy

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
        strategy_name: str,
        start_month: BillingMonth | None,
    ) -> PredictionBatchResult | None:
        records_by_resource = self._group_by_resource(records)

        if not records_by_resource:
            return None

        if start_month is None:
            all_months = sorted({r.billing_month for r in records})
            start_month = all_months[-1].next_month() if all_months else BillingMonth.from_date(2026, 1)

        chosen_strategy_name = self._resolve_strategy(
            strategy_name, list(records_by_resource.values())[0]
        )
        chosen_strategy = self.strategies.get(chosen_strategy_name)

        if chosen_strategy is None:
            return None

        all_results: list[PredictionResult] = []
        errors: list[str] = []
        total_predicted = 0.0

        for resource_id, resource_records in records_by_resource.items():
            confidence = self._compute_confidence(resource_records, chosen_strategy)

            target = start_month
            for _ in range(months):
                try:
                    strategy_result = chosen_strategy.predict(resource_records, target)
                    if strategy_result is not None:
                        result = dataclasses.replace(strategy_result, confidence=confidence)
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
        elif n >= 6:
            return "linear_trend"
        else:
            return "moving_average"

    def _compute_confidence(
        self,
        records: list[BillingRecord],
        strategy: PredictionStrategy,
    ) -> float:
        if len(records) <= 2:
            return default_confidence(len(records))
        try:
            return calculate_confidence_from_history(
                records,
                strategy.predict,
                test_window=min(3, len(records) - 2),
            )
        except Exception:
            return default_confidence(len(records))

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
        return dict(groups)
