# FinOps Integration Guide

## Overview

This guide covers integrating `billing-cost-prediction` into the `softwareone-finops-backend` Django project. Target audience: developers implementing the cost prediction pipeline.

```mermaid
flowchart LR
    A[MySQL Billing Tables] --> B[Data Adapter]
    B --> C[to_daily_rates]
    C --> D[CostAnomalyDetector]
    D --> E[PredictionEngine]
    E --> F[to_monthly_rates]
    F --> G[PredictionResult Table]
    G --> H[Django Views / API]
```

## 1. Installation

```toml
# pyproject.toml
[project]
dependencies = [
    "billing-cost-prediction>=0.1.1",
]
```

```bash
pip install billing-cost-prediction
```

## 2. Data Adapter

Bridge Django ORM models to `BillingRecord`. Create `backend/prediction/data_adapter.py`:

```python
# backend/prediction/data_adapter.py
from datetime import date
from billing_cost_prediction.types import (
    BillingRecord, BillingMonth, CloudProvider,
    ChargeType, PricingModel, PredictionResult,
)

# Cloud provider mapping
PROVIDER_MAP = {
    "alibaba": CloudProvider.ALIBABA,
    "azure": CloudProvider.AZURE,
    "aws": CloudProvider.AWS,
}

CHARGE_MAP = {
    "PostPaid": ChargeType.USAGE,
    "PrePaid": ChargeType.PURCHASE,
    "Subscription": ChargeType.SUBSCRIPTION,
}

PRICING_MAP = {
    "PayAsYouGo": PricingModel.PAYG,
    "Reserved": PricingModel.RESERVED,
    "SavingsPlan": PricingModel.SAVINGS_PLAN,
    "Spot": PricingModel.SPOT,
    "Prepaid": PricingModel.PREPAID,
}


def queryset_to_records(queryset) -> list[BillingRecord]:
    """Convert Django billing queryset to prediction engine input."""
    return [
        BillingRecord(
            resource_id=obj.instance_id or obj.resource_id,
            cloud_provider=PROVIDER_MAP.get(obj.cloud_provider, CloudProvider.AZURE),
            billing_month=_to_billing_month(obj.billing_cycle or obj.billing_month),
            cost=float(obj.pay_amount or obj.cost or 0),
            currency=getattr(obj, "currency", "CNY"),
            charge_type=CHARGE_MAP.get(obj.charge_type, ChargeType.USAGE),
            pricing_model=PRICING_MAP.get(obj.pricing_model, None),
            product_name=getattr(obj, "product_name", "") or "",
            resource_name=getattr(obj, "resource_name", "") or "",
            resource_group=getattr(obj, "resource_group", "") or "",
            service_category=getattr(obj, "service_category", "") or "",
            usage_quantity=float(getattr(obj, "usage_quantity", 0) or 0),
            tags=getattr(obj, "tags", {}) or {},
        )
        for obj in queryset
    ]


def predictions_to_models(
    results: list[PredictionResult],
    model_class,
) -> list:
    """Convert prediction results to Django model instances (unsaved)."""
    return [
        model_class(
            resource_id=r.resource_id,
            cloud_provider=r.cloud_provider.value,
            predict_month=_from_billing_month(r.predict_month),
            predicted_cost=r.predicted_cost,
            predicted_lower=r.predicted_lower,
            predicted_upper=r.predicted_upper,
            currency=r.currency,
            confidence=r.confidence,
            method=r.method,
            baseline_months=",".join(m.to_string() for m in r.baseline_months),
            baseline_cost=r.baseline_cost,
            product_name=r.product_name,
            resource_name=r.resource_name,
            resource_group=r.resource_group,
            service_category=r.service_category,
        )
        for r in results
    ]


def _to_billing_month(value) -> BillingMonth:
    if isinstance(value, date):
        return BillingMonth.from_date(value.year, value.month)
    if isinstance(value, str):
        return BillingMonth.from_string(value)
    raise ValueError(f"Cannot convert {type(value)} to BillingMonth")


def _from_billing_month(month: BillingMonth) -> date:
    return date(month.year, month.month, 1)
```

## 3. Prediction Task

Create `backend/prediction/tasks.py` — the Celery task that runs the full pipeline:

```python
# backend/prediction/tasks.py
from celery import shared_task
from django.db import transaction

from billing_cost_prediction import (
    CostAnomalyDetector,
    MAPETracker,
    PredictionEngine,
    to_daily_rates,
    to_monthly_rates,
)

from .data_adapter import (
    predictions_to_models,
    queryset_to_records,
)
from .models import BillingRecord, PredictionResultModel


@shared_task
def task__predict_all_resources(months: int = 12):
    """Main prediction task — runs for all resources across all providers."""
    engine = PredictionEngine()
    detector = CostAnomalyDetector(factor=1.5)

    # Load all billing records from DB
    qs = BillingRecord.objects.filter(
        billing_cycle__isnull=False,
        pay_amount__gt=0,
    ).order_by("instance_id", "billing_cycle")

    records = queryset_to_records(qs)

    # Step 1: Normalize day-based billing
    records = to_daily_rates(records)

    # Step 2: Detect and remove anomalies
    records = detector.filter(records)

    # Step 3: Predict
    batches = engine.predict(records, months=months)

    # Step 4: Convert back to monthly costs
    with transaction.atomic():
        for batch in batches:
            monthly = to_monthly_rates(batch.results)
            models = predictions_to_models(monthly, PredictionResultModel)
            # Upsert: replace existing predictions for same resource + month
            for m in models:
                PredictionResultModel.objects.update_or_create(
                    resource_id=m.resource_id,
                    predict_month=m.predict_month,
                    defaults={
                        "predicted_cost": m.predicted_cost,
                        "predicted_lower": m.predicted_lower,
                        "predicted_upper": m.predicted_upper,
                        "confidence": m.confidence,
                        "method": m.method,
                        "baseline_cost": m.baseline_cost,
                    },
                )

    return {
        "resources": sum(b.total_resources for b in batches),
        "predictions": sum(len(b.results) for b in batches),
        "errors": [e for b in batches for e in b.errors],
    }
```

## 4. Accuracy Tracking Task

```python
# backend/prediction/tasks.py (continued)

@shared_task
def task__track_prediction_accuracy():
    """Compare past predictions against actual costs, compute MAPE."""
    from datetime import date

    tracker = MAPETracker()

    # Find past predictions that now have actuals
    predictions = PredictionResultModel.objects.filter(
        predict_month__lte=date.today().replace(day=1),
    )
    actuals = BillingRecord.objects.filter(
        billing_cycle__in=[p.predict_month for p in predictions],
    )

    pred_records = [
        PredictionResult(
            resource_id=p.resource_id,
            cloud_provider=CloudProvider(p.cloud_provider),
            predict_month=BillingMonth.from_date(
                p.predict_month.year, p.predict_month.month
            ),
            predicted_cost=p.predicted_cost,
            method=p.method,
        )
        for p in predictions
    ]
    actual_records = queryset_to_records(actuals)

    tracker.record(pred_records, actual_records)

    return {
        "mape": tracker.mape(),
        "by_resource": tracker.mape_by_resource(),
        "count": tracker.count,
    }
```

## 5. Celery Beat Schedule

```python
# backend/dvadmin3_celery/apps.py or settings.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    "predict-all-resources": {
        "task": "prediction.tasks.task__predict_all_resources",
        "schedule": crontab(day_of_month=1, hour=2, minute=0),  # Monthly
        "kwargs": {"months": 12},
    },
    "track-prediction-accuracy": {
        "task": "prediction.tasks.task__track_prediction_accuracy",
        "schedule": crontab(day_of_month=1, hour=3, minute=0),  # Monthly
    },
}
```

## 6. Django Admin Integration

```python
# backend/prediction/admin.py
from django.contrib import admin
from .models import PredictionResultModel


@admin.register(PredictionResultModel)
class PredictionResultAdmin(admin.ModelAdmin):
    list_display = [
        "resource_id", "predict_month", "predicted_cost",
        "predicted_lower", "predicted_upper", "confidence", "method",
    ]
    list_filter = ["cloud_provider", "method", "predict_month"]
    search_fields = ["resource_id", "resource_name"]
    ordering = ["-predict_month", "resource_id"]
```

## 7. File Structure

```
backend/prediction/
├── __init__.py
├── data_adapter.py      # DB ↔ BillingRecord bridge
├── tasks.py             # Celery tasks
├── models.py            # PredictionResultModel + BillingRecord
├── views.py             # API endpoints
├── admin.py             # Django admin
└── tests/
    ├── test_data_adapter.py
    ├── test_tasks.py
    └── test_views.py
```

## 8. Migration Notes

### Removing old prediction code

```bash
# Delete old model directory
rm -rf backend/prediction/prediction_model/

# Delete dead code
rm backend/prediction/azure_views.py

# Create new prediction model
python manage.py makemigrations prediction
python manage.py migrate prediction
```

### PredictionResult model

```python
# backend/prediction/models.py
from django.db import models


class PredictionResultModel(models.Model):
    resource_id = models.CharField(max_length=128, db_index=True)
    cloud_provider = models.CharField(max_length=32, default="azure")
    predict_month = models.DateField()
    predicted_cost = models.FloatField(default=0.0)
    predicted_lower = models.FloatField(default=0.0)
    predicted_upper = models.FloatField(default=0.0)
    currency = models.CharField(max_length=8, default="CNY")
    confidence = models.FloatField(default=0.0)
    method = models.CharField(max_length=32, default="")
    baseline_cost = models.FloatField(default=0.0)
    baseline_months = models.TextField(default="")
    product_name = models.CharField(max_length=256, default="")
    resource_name = models.CharField(max_length=256, default="")
    resource_group = models.CharField(max_length=256, default="")
    service_category = models.CharField(max_length=128, default="")

    class Meta:
        db_table = "prediction_results"
        unique_together = [("resource_id", "predict_month")]
        ordering = ["-predict_month"]
        indexes = [
            models.Index(fields=["cloud_provider", "predict_month"]),
            models.Index(fields=["method"]),
        ]
```

## 9. Testing

```python
# backend/prediction/tests/test_data_adapter.py
import pytest
from billing_cost_prediction.types import BillingMonth, CloudProvider

from ..data_adapter import queryset_to_records
from ..models import BillingRecord as BillingRecordModel


class TestDataAdapter:
    def test_empty_queryset(self):
        records = queryset_to_records(BillingRecordModel.objects.none())
        assert records == []

    def test_single_record(self):
        obj = BillingRecordModel(
            instance_id="i-bp1abc123",
            cloud_provider="alibaba",
            billing_cycle="2025-01-01",
            pay_amount=310.0,
            charge_type="PrePaid",
            pricing_model="Prepaid",
            product_name="ecs.g7.xlarge",
        )
        recs = queryset_to_records([obj])
        assert len(recs) == 1
        r = recs[0]
        assert r.resource_id == "i-bp1abc123"
        assert r.cloud_provider == CloudProvider.ALIBABA
        assert r.billing_month == BillingMonth.from_date(2025, 1)
        assert r.cost == 310.0
```
