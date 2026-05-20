# cost-prediction

[![Tests](https://github.com/Visionary-Future/billing-cost-prediction/actions/workflows/pytest.yml/badge.svg)](https://github.com/Visionary-Future/billing-cost-prediction/actions/workflows/pytest.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://pypi.org/project/cost-prediction/)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)](https://github.com/Visionary-Future/billing-cost-prediction/actions/workflows/pytest.yml)

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
| `exponential_smoothing` | Noisy data, recent-weighted | 2 months |
| `linear_trend` | Consistent growth/decline | 3 months |
| `seasonal` | Annual recurring patterns | 12 months |
| `auto` (default) | Picks best based on data | — |

→ [Strategy guide with flowcharts](docs/STRATEGIES.md)

## Docs

- [Architecture & Design](docs/ARCHITECTURE.md) — data flow, component diagram, design decisions
- [Integration Guide](docs/INTEGRATION.md) — Django, SQL, CSV, custom strategies
- [Strategy Guide](docs/STRATEGIES.md) — selection flowchart, tuning, per-strategy details

## Roadmap

### ✅ Phase 1: Core Engine (done)
- [x] Type system (BillingRecord, PredictionResult, BillingMonth, enums)
- [x] 4 strategies: moving_average, exponential_smoothing, linear_trend, seasonal
- [x] Back-test based confidence scoring
- [x] Per-resource auto strategy selection
- [x] Extensible strategy protocol (Protocol, structural subtyping)
- [x] Unit + integration tests (105 tests, 95%+ coverage)
- [x] Architecture refactoring (O(n) iteration, sort-once, build_result helper)
- [x] Python 3.10+ support
- [x] Architecture docs with flowcharts (Mermaid)
- [x] Pre-commit hooks (ruff + mypy)

### 🔜 Phase 2: Production Readiness (next)
- [ ] PyPI publish (`pip install cost-prediction`)
- [x] CI pipeline (GitHub Actions: pytest/ruff/mypy matrix)
- [x] Coverage reporting (sticky PR comment)
- [x] Integration guide (Django, SQL, CSV, custom strategy)

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

### 🔮 Phase 3: Algorithm Enhancements (done)
- [x] ExponentialSmoothingStrategy
- [x] CostAnomalyDetector (pre-filter anomalous months)
- [x] StrategyEnsemble (multi-strategy voting)
- [x] Prediction accuracy tracking (MAPE)
- [x] Day-based billing normalization (to_daily_rates / to_monthly_rates)

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
