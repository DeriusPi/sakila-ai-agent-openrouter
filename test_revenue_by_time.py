from tools.data.get_revenue_by_time import get_revenue_by_time
from tools.tool_definitions import TOOL_DEFINITIONS, TOOL_FUNCTIONS


def test_month_range():
    result = get_revenue_by_time(
        start_date="2005-05-01",
        end_date="2005-07-31",
        group_by="month",
    )

    assert result["total_revenue"] == 42822.24
    assert result["total_transactions"] == 10176

    monthly = {
        row["group"]: row["revenue"]
        for row in result["grouped_revenue"]
    }

    assert monthly["2005-05"] == 4823.44
    assert monthly["2005-06"] == 9629.89
    assert monthly["2005-07"] == 28368.91

    print("PASS: May-July revenue")


def test_may_category():
    result = get_revenue_by_time(
        start_date="2005-05-01",
        end_date="2005-05-31",
        group_by="category",
    )

    assert result["total_revenue"] == 4823.44
    assert result["total_transactions"] == 1156

    top = result["highest_revenue_group"]

    assert top["group"] == "Action"
    assert top["revenue"] == 371.13

    print("PASS: May category revenue")


def test_june():
    result = get_revenue_by_time(
        start_date="2005-06-01",
        end_date="2005-06-30",
        group_by="month",
    )

    assert result["total_revenue"] == 9629.89
    assert result["total_transactions"] == 2311

    print("PASS: June revenue")


def test_quarter():
    result = get_revenue_by_time(
        start_date="2005-05-01",
        end_date="2005-07-31",
        group_by="quarter",
    )

    assert result["total_revenue"] == 42822.24
    assert len(result["grouped_revenue"]) == 2

    print("PASS: Quarter grouping")


def test_year():
    result = get_revenue_by_time(
        start_date="2005-01-01",
        end_date="2005-12-31",
        group_by="year",
    )

    assert len(result["grouped_revenue"]) >= 1
    assert result["total_revenue"] > 0

    print("PASS: Year grouping")


def test_tool_registry():
    names = {
        tool["name"]
        for tool in TOOL_DEFINITIONS
    }

    assert "get_revenue_by_time" in names
    assert "get_revenue_by_time" in TOOL_FUNCTIONS

    print("PASS: Tool registry")


def test_invalid_group():
    try:
        get_revenue_by_time(
            start_date="2005-05-01",
            end_date="2005-05-31",
            group_by="invalid",
        )
    except ValueError:
        print("PASS: Invalid group rejected")
        return

    raise AssertionError("Invalid group_by was not rejected")


if __name__ == "__main__":
    print("=" * 70)
    print("TIME-BASED REVENUE — NO LLM TEST")
    print("=" * 70)

    test_month_range()
    test_may_category()
    test_june()
    test_quarter()
    test_year()
    test_tool_registry()
    test_invalid_group()

    print("=" * 70)
    print("ALL NO-LLM TESTS PASSED")
    print("=" * 70)
