from dataclasses import dataclass, field


@dataclass
class BudgetBreakdown:
    accommodation: float = 0.0
    meals: float = 0.0
    transport: float = 0.0
    tickets: float = 0.0
    other: float = 0.0


@dataclass
class BudgetResult:
    total: float
    breakdown: BudgetBreakdown
    over_budget: bool = False
    suggestions: list[str] = field(default_factory=list)


ACCOMMODATION_PER_NIGHT = 300.0
MEALS_PER_DAY = 150.0
TRANSPORT_PER_DAY = 50.0


def budget_estimate(
    trip_days: int,
    ticket_prices: list[float] | None = None,
    transport_mode: str = "public",
    budget_limit: float | None = None,
) -> BudgetResult:
    nights = max(trip_days - 1, 0)
    accommodation = nights * ACCOMMODATION_PER_NIGHT
    meals = trip_days * MEALS_PER_DAY
    transport_rate = TRANSPORT_PER_DAY if transport_mode == "public" else 200.0
    transport = trip_days * transport_rate
    tickets = sum(ticket_prices) if ticket_prices else 0.0

    total = accommodation + meals + transport + tickets
    breakdown = BudgetBreakdown(
        accommodation=accommodation,
        meals=meals,
        transport=transport,
        tickets=tickets,
    )

    over_budget = budget_limit is not None and total > budget_limit
    suggestions: list[str] = []
    if over_budget and budget_limit is not None:
        diff = total - budget_limit
        suggestions.append(f"超出预算 {diff:.0f} 元")
        if transport_mode != "public":
            suggestions.append("建议使用公共交通以节省费用")
        if accommodation > 0:
            suggestions.append("可以考虑选择经济型住宿")

    return BudgetResult(
        total=total,
        breakdown=breakdown,
        over_budget=over_budget,
        suggestions=suggestions,
    )
