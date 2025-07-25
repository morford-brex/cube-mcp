"""Unit tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from mcp_cube_server.server import Filter, Query, TimeDimension


class TestTimeDimension:
    """Test cases for TimeDimension model."""

    def test_valid_time_dimension(self) -> None:
        """Test creating a valid TimeDimension."""
        td = TimeDimension(
            dimension="Orders.created_at",
            granularity="day",
            dateRange=["2024-01-01", "2024-01-31"],
        )

        assert td.dimension == "Orders.created_at"
        assert td.granularity == "day"
        assert td.dateRange == ["2024-01-01", "2024-01-31"]

    def test_time_dimension_with_string_date_range(self) -> None:
        """Test TimeDimension with string date range."""
        td = TimeDimension(
            dimension="Orders.created_at",
            granularity="month",
            dateRange="last 7 days",
        )

        assert td.dateRange == "last 7 days"

    def test_invalid_granularity(self) -> None:
        """Test TimeDimension with invalid granularity."""
        with pytest.raises(ValidationError) as exc_info:
            TimeDimension(
                dimension="Orders.created_at",
                granularity="invalid",  # type: ignore
                dateRange=["2024-01-01", "2024-01-31"],
            )

        assert "Input should be" in str(exc_info.value)

    def test_missing_required_fields(self) -> None:
        """Test TimeDimension with missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            TimeDimension()  # type: ignore

        errors = exc_info.value.errors()
        assert len(errors) == 3  # dimension, granularity, dateRange

    def test_exclude_none_config(self) -> None:
        """Test that None values are excluded from serialization."""
        td = TimeDimension(
            dimension="Orders.created_at",
            granularity="day",
            dateRange=["2024-01-01", "2024-01-31"],
        )

        dumped = td.model_dump()
        assert None not in dumped.values()


class TestFilter:
    """Test cases for Filter model."""

    def test_valid_filter(self) -> None:
        """Test creating a valid Filter."""
        f = Filter(
            dimension="Orders.status",
            granularity="day",
            dateRange=["2024-01-01", "2024-01-31"],
        )

        assert f.dimension == "Orders.status"
        assert f.granularity == "day"
        assert f.dateRange == ["2024-01-01", "2024-01-31"]

    def test_filter_equals_time_dimension(self) -> None:
        """Test that Filter has same structure as TimeDimension."""
        # Both should have same fields and validation
        filter_fields = set(Filter.model_fields.keys())
        time_dim_fields = set(TimeDimension.model_fields.keys())

        assert filter_fields == time_dim_fields


class TestQuery:
    """Test cases for Query model."""

    def test_valid_query_with_all_fields(self) -> None:
        """Test creating a valid Query with all fields."""
        td = TimeDimension(
            dimension="Orders.created_at",
            granularity="day",
            dateRange=["2024-01-01", "2024-01-31"],
        )

        query = Query(
            measures=["Orders.count", "Orders.total_amount"],
            dimensions=["Orders.status"],
            timeDimensions=[td],
            limit=100,
            offset=0,
            order={"Orders.count": "desc"},
            ungrouped=False,
        )

        assert query.measures == ["Orders.count", "Orders.total_amount"]
        assert query.dimensions == ["Orders.status"]
        assert len(query.timeDimensions) == 1
        assert query.limit == 100
        assert query.offset == 0
        assert query.order == {"Orders.count": "desc"}
        assert query.ungrouped is False

    def test_query_with_defaults(self) -> None:
        """Test Query with default values."""
        query = Query()

        assert query.measures == []
        assert query.dimensions == []
        assert query.timeDimensions == []
        assert query.limit == 500
        assert query.offset == 0
        assert query.order == {}
        assert query.ungrouped is False

    def test_query_serialization(self) -> None:
        """Test Query serialization with exclude_none."""
        query = Query(
            measures=["Orders.count"],
            dimensions=["Orders.status"],
        )

        dumped = query.model_dump(exclude_none=True)

        # Should only include non-default values
        assert "measures" in dumped
        assert "dimensions" in dumped
        assert "timeDimensions" in dumped  # Empty list is not None
        assert "limit" in dumped  # Has default value
        assert "offset" in dumped  # Has default value

    def test_query_order_validation(self) -> None:
        """Test Query order field validation."""
        query = Query(order={"Orders.count": "asc", "Orders.total_amount": "desc"})

        assert query.order["Orders.count"] == "asc"
        assert query.order["Orders.total_amount"] == "desc"

    def test_query_invalid_order_direction(self) -> None:
        """Test Query with invalid order direction."""
        with pytest.raises(ValidationError) as exc_info:
            Query(order={"Orders.count": "invalid"})  # type: ignore

        assert "Input should be" in str(exc_info.value)

    def test_query_with_multiple_time_dimensions(self) -> None:
        """Test Query with multiple time dimensions."""
        td1 = TimeDimension(
            dimension="Orders.created_at",
            granularity="day",
            dateRange="last 7 days",
        )
        td2 = TimeDimension(
            dimension="Orders.updated_at",
            granularity="hour",
            dateRange="today",
        )

        query = Query(timeDimensions=[td1, td2])

        assert len(query.timeDimensions) == 2
        assert query.timeDimensions[0].dimension == "Orders.created_at"
        assert query.timeDimensions[1].dimension == "Orders.updated_at"

    def test_query_model_dump_by_alias(self) -> None:
        """Test Query serialization with by_alias parameter."""
        query = Query(
            measures=["Orders.count"],
            limit=10,
        )

        # The model should serialize properly with by_alias
        dumped = query.model_dump(by_alias=True, exclude_none=True)

        assert "measures" in dumped
        assert "limit" in dumped
        assert dumped["limit"] == 10
