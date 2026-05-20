"""Core data types for the cost prediction engine. Framework-agnostic, zero dependencies."""

from dataclasses import dataclass, field
from enum import Enum
from functools import total_ordering


class CloudProvider(str, Enum):
    ALIBABA = "alibaba"
    AZURE = "azure"
    AWS = "aws"
    HUAWEI = "huawei"
    TENCENT = "tencent"


class ChargeType(str, Enum):
    USAGE = "usage"
    PURCHASE = "purchase"
    SUBSCRIPTION = "subscription"


class PricingModel(str, Enum):
    PAYG = "payg"
    RESERVED = "reserved"
    SAVINGS_PLAN = "savings_plan"
    SPOT = "spot"
    PREPAID = "prepaid"


@total_ordering
@dataclass(frozen=True, order=False)
class BillingMonth:
    """YYYY-MM billing month, comparable and hashable."""

    year: int
    month: int

    def __post_init__(self) -> None:
        if not (1 <= self.month <= 12):
            raise ValueError(f"month must be 1-12, got {self.month}")
        if self.year < 2000 or self.year > 2100:
            raise ValueError(f"year must be 2000-2100, got {self.year}")

    @classmethod
    def from_string(cls, value: str) -> "BillingMonth":
        year_str, month_str = value.strip().split("-")
        return cls(year=int(year_str), month=int(month_str))

    @classmethod
    def from_date(cls, year: int, month: int) -> "BillingMonth":
        return cls(year=year, month=month)

    def to_string(self) -> str:
        return f"{self.year:04d}-{self.month:02d}"

    def next_month(self) -> "BillingMonth":
        if self.month == 12:
            return BillingMonth(year=self.year + 1, month=1)
        return BillingMonth(year=self.year, month=self.month + 1)

    def months_ahead(self, n: int) -> "BillingMonth":
        result = self
        for _ in range(n):
            result = result.next_month()
        return result

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BillingMonth):
            return NotImplemented
        return (self.year, self.month) == (other.year, other.month)

    def __lt__(self, other: "BillingMonth") -> bool:
        return (self.year, self.month) < (other.year, other.month)

    def __hash__(self) -> int:
        return hash((self.year, self.month))

    def __repr__(self) -> str:
        return self.to_string()


@dataclass(frozen=True)
class BillingRecord:
    """A single billing record — input to the prediction engine."""

    resource_id: str
    cloud_provider: CloudProvider
    billing_month: BillingMonth
    cost: float
    currency: str = "CNY"
    charge_type: ChargeType = ChargeType.USAGE
    pricing_model: PricingModel | None = None
    product_name: str = ""
    resource_name: str = ""
    resource_group: str = ""
    service_category: str = ""
    tags: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PredictionResult:
    """A single prediction — output of the prediction engine."""

    resource_id: str
    cloud_provider: CloudProvider
    predict_month: BillingMonth
    predicted_cost: float
    currency: str = "CNY"
    confidence: float = 0.0
    method: str = ""
    baseline_months: list[BillingMonth] = field(default_factory=list)
    baseline_cost: float = 0.0
    product_name: str = ""
    resource_name: str = ""
    resource_group: str = ""
    service_category: str = ""
    pricing_model: PricingModel | None = None
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PredictionBatchResult:
    """Batched prediction output with per-provider summaries."""

    provider: CloudProvider
    results: list[PredictionResult] = field(default_factory=list)
    total_resources: int = 0
    total_predicted: float = 0.0
    errors: list[str] = field(default_factory=list)
