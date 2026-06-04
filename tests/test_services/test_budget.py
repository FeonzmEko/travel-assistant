from backend.services.budget import budget_estimate


def test_budget_basic() -> None:
    result = budget_estimate(trip_days=3, ticket_prices=[60.0, 0.0, 40.0])
    assert result.breakdown.accommodation == 600.0
    assert result.breakdown.meals == 450.0
    assert result.breakdown.transport == 150.0
    assert result.breakdown.tickets == 100.0
    assert result.total == 1300.0
    assert result.over_budget is False


def test_budget_one_day() -> None:
    result = budget_estimate(trip_days=1)
    assert result.breakdown.accommodation == 0.0
    assert result.breakdown.meals == 150.0


def test_budget_over_limit() -> None:
    result = budget_estimate(trip_days=3, budget_limit=1000.0)
    assert result.over_budget is True
    assert len(result.suggestions) > 0


def test_budget_taxi_mode() -> None:
    result = budget_estimate(trip_days=2, transport_mode="taxi")
    assert result.breakdown.transport == 400.0


def test_budget_no_tickets() -> None:
    result = budget_estimate(trip_days=2)
    assert result.breakdown.tickets == 0.0
