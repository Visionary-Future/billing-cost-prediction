"""cost-prediction — Cloud cost prediction engine.

Framework-agnostic, strategy-based cost forecasting for multi-cloud billing data.

Usage:
    from cost_prediction import PredictionEngine
    from cost_prediction.types import BillingRecord, BillingMonth, CloudProvider

    engine = PredictionEngine()
    records = [
        BillingRecord(
            resource_id="res-001",
            cloud_provider=CloudProvider.AZURE,
            billing_month=BillingMonth.from_string("2026-04"),
            cost=1234.56,
        ),
    ]
    results = engine.predict(records, months=12)
"""

from cost_prediction.engine import PredictionEngine
from cost_prediction.types import (
    BillingMonth,
    BillingRecord,
    CloudProvider,
    PredictionBatchResult,
    PredictionResult,
)

__all__ = [
    "PredictionEngine",
    "BillingRecord",
    "BillingMonth",
    "CloudProvider",
    "PredictionResult",
    "PredictionBatchResult",
]
