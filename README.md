# cost-prediction

Framework-agnostic cloud cost prediction engine. Strategy-based, zero dependencies.

## Quick Start

```python
from cost_prediction import PredictionEngine, BillingRecord, BillingMonth, CloudProvider

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
for batch in results:
    for r in batch.results:
        print(f"{r.predict_month}: {r.predicted_cost:.2f} ({r.method}, confidence={r.confidence})")
```

## Strategies

| Strategy | Best For | Min History |
|----------|----------|-------------|
| `moving_average` | Stable workloads | 1 month |
| `linear_trend` | Consistent growth/decline | 3 months |
| `seasonal` | Annual recurring patterns | 12 months |
| `auto` (default) | Picks best based on data | — |

## Roadmap

### ✅ Phase 1: Core Engine (done)
- [x] Type system (BillingRecord, PredictionResult, BillingMonth, enums)
- [x] 3 strategies: moving_average, linear_trend, seasonal
- [x] Back-test based confidence scoring
- [x] Auto strategy selection
- [x] Extensible strategy protocol
- [x] Unit + integration tests (20 tests)
- [x] Code review: off-by-one fix, dead code removal, O(n) date iteration
- [x] Python 3.10+ support

### 🔜 Phase 2: Production Readiness (next)
- [ ] PyPI publish (`pip install cost-prediction`)
- [ ] CI pipeline (GitHub Actions: pytest/ruff/mypy)
- [ ] Coverage reporting

### 🔗 Django Integration (cross-repo)

**Repo:** `softwareone-finops-backend`

- [ ] Remove `backend/prediction/prediction_model/` directory
- [ ] Remove `backend/prediction/azure_views.py` (dead code)
- [ ] Add `cost-prediction` to `pyproject.toml` dependencies
- [ ] Create `backend/prediction/data_adapter.py` (DB ↔ engine bridge)
- [ ] Rewrite `task__multi_cloud_bill_predict` using engine + adapter
- [ ] Change task from "delete-all + rebuild" to `update_or_create` upsert
- [ ] Add `unique_together` constraint on prediction model
- [ ] Remove unused model fields (billing_model, region, availability_zone, provider_metadata)
- [ ] Unify actual-cost queries across Alibaba/Azure in Views
- [ ] Integration tests for data_adapter, tasks, views

### 🔮 Phase 3: Algorithm Enhancements (future)
- [ ] ExponentialSmoothingStrategy
- [ ] CostAnomalyDetector (pre-filter anomalous months)
- [ ] StrategyEnsemble (multi-strategy voting)
- [ ] Prediction accuracy tracking (MAPE)
- [ ] ML integration (sklearn-based strategies)

## Development

```bash
# install in dev mode
pip install -e ".[dev]"

# run tests
pytest -v

# lint
ruff check .
mypy .
```
