# billing-cost-prediction

[![Tests](https://github.com/Visionary-Future/billing-cost-prediction/actions/workflows/pytest.yml/badge.svg)](https://github.com/Visionary-Future/billing-cost-prediction/actions/workflows/pytest.yml)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://pypi.org/project/billing-cost-prediction/)
[![Coverage](https://img.shields.io/badge/coverage-95%25-brightgreen)](https://github.com/Visionary-Future/billing-cost-prediction/actions/workflows/pytest.yml)

Framework-agnostic cloud cost prediction engine. Strategy-based, zero dependencies.

## Quick Start

```python
from billing_cost_prediction import PredictionEngine, BillingRecord, BillingMonth, CloudProvider

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

## Features

### Prediction Engine
- **4 strategies**: moving_average, exponential_smoothing, linear_trend, seasonal
- **Auto selection**: per-resource strategy based on history length
- **Prediction intervals**: 95% confidence bounds on every prediction
- **Back-test confidence**: confidence scores from historical accuracy

### Anomaly Detection
- **IQR-based**: Tukey's fences, configurable sensitivity
- **Per-resource**: independent detection per resource
- **Pre-filtering**: remove spike months before prediction

### Normalization
- **Day-based billing**: `to_daily_rates` / `to_monthly_rates` — eliminate calendar effects
- **Unit economics**: `to_unit_cost` — cost per unit for fair comparison
- **Immutable**: all functions return new objects, zero side effects

### Accuracy & Ensemble
- **MAPE tracking**: per-resource and aggregate accuracy
- **Strategy ensemble**: mean / median / weighted voting
- **Resource + month validation**: safe pairing of predictions vs actuals

### Quality
- **Python 3.10+**, zero external dependencies
- **97%+ test coverage**, mypy strict mode, ruff linted
- **CI**: test matrix (3.10–3.13), CodeQL, smoke test, auto-publish to PyPI
- **Pre-commit hooks**: ruff + mypy on every commit

## Docs

- [Architecture & Design](docs/ARCHITECTURE.md) — data flow, component diagram, design decisions
- [Strategy Guide](docs/STRATEGIES.md) — formulas, selection flowchart, tuning
- [Integration Guide](docs/INTEGRATION.md) — Django, SQL, CSV, custom strategies
- [FinOps Integration](docs/FINOPS_INTEGRATION.md) — Celery tasks, data adapter, admin setup

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
