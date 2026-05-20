# Strategies

## Before You Predict: Normalization

For day-based billing (e.g. Alibaba prepaid ECS), normalize monthly costs to daily rates first. Otherwise, calendar variation (31-day vs 28-day months) looks like cost volatility and confuses the strategies.

```
records  →  to_daily_rates(records)  →  engine.predict()  →  to_monthly_rates(results)
```

See [Integration Guide](INTEGRATION.md#day-based-billing-alibaba-prepaid-ecs) for the full pipeline.

## Selection Flow

```mermaid
flowchart TD
    A[How many months<br/>of history?] --> |12+| B{Strong seasonal<br/>pattern?}
    A --> |6-11| C{Clear linear<br/>trend?}
    A --> |2-5| D{Recent data more<br/>relevant?}
    A --> |1| E[Moving Average]

    B --> |Yes| S1[Seasonal]
    B --> |No| C

    C --> |Yes| S2[Linear Trend]
    C --> |No| S3[Exponential Smoothing]

    D --> |Yes| S3
    D --> |No| S4[Moving Average]

    style S1 fill:#f9f,stroke:#333
    style S2 fill:#9f9,stroke:#333
    style S3 fill:#ff9,stroke:#333
    style S4 fill:#9ff,stroke:#333
```

## Strategy Comparison

| Strategy | Min Data | Best For | How It Works | Alpha / Window |
|----------|----------|----------|-------------|----------------|
| `moving_average` | 1 month | Stable, flat workloads | Mean of last N months | `window_months=3` |
| `exponential_smoothing` | 2 months | Noisy data, gradual shifts | α × last + (1-α) × smoothed | `alpha=0.3` |
| `linear_trend` | 3 months | Consistent growth or decline | Linear regression + extrapolate | `window_months=6` |
| `seasonal` | 12 months | Annual patterns (retail, tax) | Seasonal factor × recent average | `window_months=12` |

## Strategy Details

### Moving Average

```mermaid
flowchart LR
    A[Jan: $100] --> B[Feb: $100]
    B --> C[Mar: $100]
    C --> D[Predict Apr]
    D --> |"($100+$100+$100)/3"| E[$100]
```

Simplest strategy. Takes the arithmetic mean of the last `window_months`. Zero parameters to tune. The fallback when nothing else fits.

**Use when**: Costs are stable. No growth, no seasonality, no noise.

### Exponential Smoothing

```mermaid
flowchart TD
    A["S₁ = $100<br/>(first month)"] --> B["S₂ = 0.3×$110 + 0.7×$100 = $103"]
    B --> C["S₃ = 0.3×$120 + 0.7×$103 = $108.1"]
    C --> D["Forecast = S₃ = $108.1"]

    style A fill:#ff9,stroke:#333
    style B fill:#ff9,stroke:#333
    style C fill:#ff9,stroke:#333
    style D fill:#9f9,stroke:#333
```

Weights recent observations more heavily. Older data decays exponentially: weight at lag k = α(1-α)^k.

**Alpha tuning**:
- `α = 0.1` — heavy smoothing, slow to respond (stable series)
- `α = 0.3` — moderate smoothing (default)
- `α = 0.8` — light smoothing, fast to respond (volatile series)

**Use when**: Recent months are more indicative than older ones. Moderate noise.

### Linear Trend

```mermaid
flowchart LR
    subgraph Data
        A["Jan: $100<br/>(x=0)"] --> B["Feb: $110<br/>(x=1)"]
        B --> C["Mar: $120<br/>(x=2)"]
    end
    subgraph Model
        D["slope = $10/month"]
        E["intercept = $100"]
    end
    subgraph Forecast
        F["Apr (x=3): $130"]
        G["May (x=4): $140"]
    end
    Data --> Model --> Forecast
```

Fits `y = ax + b` via least squares, then extrapolates. Predictions clamp to 0 for negative trends.

**Use when**: Consistent month-over-month growth or decline. 3 months minimum.

### Seasonal

```mermaid
flowchart TD
    A[Last 12 months of history] --> B[Compute monthly averages]
    B --> C[Detect seasonal factor:<br/>month_avg / overall_avg]
    C --> D[Multiply by recent 3-month average]
    D --> E[Forecast = recent_avg × seasonal_factor]
```

Detects year-over-year patterns. If January is typically 150% of the annual average, upcoming January predictions get a 1.5× multiplier.

**Use when**: Annual recurring patterns. 12 months minimum.

## Auto Strategy Selection

When `strategy="auto"` (default), the engine picks based on data volume:

```
n >= 12  → seasonal
n >= 6   → linear_trend
n >= 2   → exponential_smoothing
n >= 1   → moving_average
```

Selection is per-resource, so a batch with mixed history lengths gets per-resource strategy assignment.

## Custom Strategy Parameters

```python
from cost_prediction import PredictionEngine
from cost_prediction.strategies import ExponentialSmoothingStrategy, LinearTrendStrategy

engine = PredictionEngine(strategies={
    "exponential_smoothing": ExponentialSmoothingStrategy(alpha=0.5),
    "moving_average": MovingAverageStrategy(window_months=6),
    "linear_trend": LinearTrendStrategy(window_months=12),
    "seasonal": SeasonalStrategy(window_months=24),
})
```
