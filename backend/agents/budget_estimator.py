import json

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from backend.config import settings
from backend.services.budget import BudgetResult, budget_estimate

SYSTEM_PROMPT = "你是一个专业的旅行预算分析专家。估算行程费用并给出预算建议，返回JSON格式的预算报告。"


class BudgetEstimateInput(BaseModel):
    trip_days: int = Field(description="行程天数")
    ticket_prices: list[float] | None = Field(default=None, description="门票价格列表")
    transport_mode: str = Field(default="public", description="交通方式：public或taxi")
    budget_limit: float | None = Field(default=None, description="预算上限")


@tool(args_schema=BudgetEstimateInput)
def estimate_budget_tool(
    trip_days: int,
    ticket_prices: list[float] | None = None,
    transport_mode: str = "public",
    budget_limit: float | None = None,
) -> str:
    """估算旅行预算"""
    result = budget_estimate(
        trip_days=trip_days,
        ticket_prices=ticket_prices,
        transport_mode=transport_mode,
        budget_limit=budget_limit,
    )
    return json.dumps({
        "total": result.total,
        "breakdown": {
            "accommodation": result.breakdown.accommodation,
            "meals": result.breakdown.meals,
            "transport": result.breakdown.transport,
            "tickets": result.breakdown.tickets,
        },
        "over_budget": result.over_budget,
        "suggestions": result.suggestions,
    }, ensure_ascii=False)


def create_budget_estimator_agent():  # type: ignore[no-untyped-def]
    llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0,
    )
    return create_react_agent(llm, [estimate_budget_tool], prompt=SYSTEM_PROMPT)


async def estimate_trip_budget(
    trip_days: int,
    ticket_prices: list[float] | None = None,
    transport_mode: str = "public",
    budget_limit: float | None = None,
) -> BudgetResult:
    return budget_estimate(
        trip_days=trip_days,
        ticket_prices=ticket_prices,
        transport_mode=transport_mode,
        budget_limit=budget_limit,
    )
