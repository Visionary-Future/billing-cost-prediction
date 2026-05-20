"""Unit tests for core data types."""

import pytest

from cost_prediction.types import BillingMonth, CloudProvider, PredictionBatchResult


class TestBillingMonth:
    def test_from_string(self) -> None:
        m = BillingMonth.from_string("2026-04")
        assert m.year == 2026
        assert m.month == 4

    def test_from_date(self) -> None:
        m = BillingMonth.from_date(2026, 4)
        assert m.year == 2026
        assert m.month == 4

    def test_to_string(self) -> None:
        m = BillingMonth.from_date(2026, 12)
        assert m.to_string() == "2026-12"

    def test_repr(self) -> None:
        m = BillingMonth.from_date(2026, 1)
        assert repr(m) == "2026-01"

    def test_next_month(self) -> None:
        m = BillingMonth.from_date(2026, 12)
        n = m.next_month()
        assert n.year == 2027
        assert n.month == 1

    def test_months_ahead(self) -> None:
        m = BillingMonth.from_date(2026, 1)
        result = m.months_ahead(3)
        assert result.year == 2026
        assert result.month == 4

    def test_months_ahead_cross_year(self) -> None:
        m = BillingMonth.from_date(2026, 11)
        result = m.months_ahead(3)
        assert result.year == 2027
        assert result.month == 2

    def test_equality(self) -> None:
        a = BillingMonth.from_date(2026, 1)
        b = BillingMonth.from_date(2026, 1)
        assert a == b

    def test_equality_non_billingmonth(self) -> None:
        m = BillingMonth.from_date(2026, 1)
        assert m != "2026-01"

    def test_ordering_same_year(self) -> None:
        a = BillingMonth.from_date(2026, 1)
        b = BillingMonth.from_date(2026, 6)
        assert a < b

    def test_ordering_cross_year(self) -> None:
        a = BillingMonth.from_date(2025, 12)
        b = BillingMonth.from_date(2026, 1)
        assert a < b

    def test_hashable(self) -> None:
        s = {BillingMonth.from_date(2026, 1), BillingMonth.from_date(2026, 1)}
        assert len(s) == 1

    def test_invalid_month_raises(self) -> None:
        with pytest.raises(ValueError):
            BillingMonth.from_date(2026, 0)

    def test_invalid_year_too_low_raises(self) -> None:
        with pytest.raises(ValueError):
            BillingMonth.from_date(1999, 1)

    def test_invalid_year_too_high_raises(self) -> None:
        with pytest.raises(ValueError):
            BillingMonth.from_date(2101, 1)


class TestPredictionBatchResult:
    def test_required_provider(self) -> None:
        batch = PredictionBatchResult(provider=CloudProvider.AZURE)
        assert batch.provider == CloudProvider.AZURE
        assert batch.results == []
        assert batch.total_resources == 0
