# Architecture

## Overview

cost-prediction is a framework-agnostic cloud cost prediction engine built on the Strategy pattern via Protocol. Zero external dependencies.

```
┌─────────────────────────────────────────────────────────┐
│                    PredictionEngine                      │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Group by    │  │ Resolve      │  │ Compute       │  │
│  │ Provider /  │  │ Strategy     │  │ Confidence    │  │
│  │ Resource    │  │ (per-res)    │  │ (back-test)   │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
└────────────────────────┬────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
   │ Moving   │  │ Expo-    │  │ Linear   │  │ Seasonal     │
   │ Average  │  │ nential  │  │ Trend    │  │              │
   │          │  │ Smooth.  │  │          │  │              │
   └──────────┘  └──────────┘  └──────────┘  └──────────────┘
          ▲              ▲              ▲              ▲
          └──────────────┴──────────────┴──────────────┘
                   PredictionStrategy (Protocol)
```

## Data Flow

```mermaid
flowchart TD
    A[list of BillingRecord] --> B{Group by Provider}
    B --> |Azure records| C1[_predict_for_provider]
    B --> |Alibaba records| C2[_predict_for_provider]
    B --> |AWS records| C3[_predict_for_provider]

    C1 --> D{Group by Resource<br/>+ Sort by month}
    D --> E[For each Resource]

    E --> F{Resolve Strategy<br/>per-resource}
    F --> |12+ months| G1[Seasonal]
    F --> |6-11 months| G2[LinearTrend]
    F --> |2-5 months| G3[ExponentialSmoothing]
    F --> |1 month| G4[MovingAverage]

    G1 --> H[For each month in horizon]
    G2 --> H
    G3 --> H
    G4 --> H

    H --> I[Strategy.predict]
    I --> J[dataclasses.replace<br/>inject confidence]
    J --> K[PredictionBatchResult]
```

## Component Diagram

```mermaid
classDiagram
    class BillingRecord {
        +str resource_id
        +CloudProvider cloud_provider
        +BillingMonth billing_month
        +float cost
        +str currency
        +ChargeType charge_type
        +PricingModel? pricing_model
        +str product_name
        +str resource_name
    }

    class PredictionResult {
        +str resource_id
        +CloudProvider cloud_provider
        +BillingMonth predict_month
        +float predicted_cost
        +float confidence
        +str method
        +list~BillingMonth~ baseline_months
        +float baseline_cost
    }

    class PredictionBatchResult {
        +CloudProvider provider
        +list~PredictionResult~ results
        +int total_resources
        +float total_predicted
        +list~str~ errors
    }

    class PredictionEngine {
        +dict strategies
        +predict(records, months, strategy, start_month) list
        -_group_by_provider(records) dict
        -_group_by_resource(records) dict
        -_resolve_strategy(name, records) str
        -_compute_confidence(records, strategy) float
    }

    class PredictionStrategy {
        <<Protocol>>
        +str name
        +predict(records, target_month) PredictionResult?
    }

    class MovingAverageStrategy
    class ExponentialSmoothingStrategy
    class LinearTrendStrategy
    class SeasonalStrategy

    PredictionEngine --> PredictionStrategy : uses
    PredictionStrategy <|.. MovingAverageStrategy : implements
    PredictionStrategy <|.. ExponentialSmoothingStrategy : implements
    PredictionStrategy <|.. LinearTrendStrategy : implements
    PredictionStrategy <|.. SeasonalStrategy : implements
    PredictionBatchResult *-- PredictionResult : contains
    BillingRecord --> BillingMonth : keyed by
    PredictionResult --> BillingMonth : predicts
```

## Layer Architecture

```
┌─────────────────────────────────────────────┐
│                   Public API                 │
│  PredictionEngine, BillingRecord, types      │
├─────────────────────────────────────────────┤
│                Orchestration                  │
│  engine.py — grouping, routing, confidence   │
├─────────────────────────────────────────────┤
│                Strategy Layer                 │
│  moving_average, exponential_smoothing,      │
│  linear_trend, seasonal                      │
├─────────────────────────────────────────────┤
│                Domain Types                   │
│  BillingMonth, BillingRecord,                │
│  PredictionResult, enums                     │
└─────────────────────────────────────────────┘
```

## Key Design Decisions

### Protocol > ABC

Strategies use `typing.Protocol` instead of abstract base classes. Each strategy only needs `name` and `predict()` — no inheritance required. New strategies are discovered structurally, not by registration.

### Per-Resource Strategy Selection

Different resources in the same batch may have different history lengths (one has 24 months, another has 3). The engine resolves the best strategy for each resource individually — not one strategy for the whole batch.

### Sort Once

Records are sorted by `billing_month` once in `_group_by_resource`. Strategies assume sorted input and never re-sort, avoiding `O(resources × months × n log n)` redundant work.

### Immutable Data

All data types are `frozen=True` dataclasses. Predictions are constructed once and never mutated. `dataclasses.replace()` is used by the engine to inject confidence without modifying the original result.

### Back-Test Confidence

Confidence scores come from back-testing — the prediction function is tested against known historical months. No external labeled data required. The test window scales with data size: `max(3, min(12, n/4))`.

```

The Mermaid diagrams won't show the actual visual output in this text — see the rendered Markdown on GitHub.

