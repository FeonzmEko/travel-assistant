import json

from backend.agents.budget_estimator import estimate_budget_tool


def test_estimate_budget_tool() -> None:
    result = estimate_budget_tool.invoke(
        {"trip_days": 3, "ticket_prices": [60.0, 0.0], "transport_mode": "public"}
    )
    data = json.loads(result)
    assert data["total"] > 0
    assert "breakdown" in data
    assert data["breakdown"]["accommodation"] == 600.0
    assert data["breakdown"]["tickets"] == 60.0


def test_estimate_budget_tool_over_budget() -> None:
    result = estimate_budget_tool.invoke(
        {"trip_days": 3, "budget_limit": 500.0}
    )
    data = json.loads(result)
    assert data["over_budget"] is True
    assert len(data["suggestions"]) > 0
