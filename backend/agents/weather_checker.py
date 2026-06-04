"""天气查询 Agent — M9

专门负责天气查询与影响评估，拥有独立的 LLM 推理能力。
可用工具：高德天气 API。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from backend.config import settings
from backend.services.weather import weather_query


# --------------- Tool input schema ---------------

class WeatherQueryInput(BaseModel):
    city: str = Field(description="城市名称或城市编码，如 '北京' 或 '110000'")


# --------------- Tool ---------------

@tool(args_schema=WeatherQueryInput)
async def weather_query_tool(city: str) -> str:
    """查询城市未来几天的天气预报，包括日间/夜间天气、温度、风力等信息。"""
    forecasts = await weather_query(city=city)
    return json.dumps([asdict(f) for f in forecasts], ensure_ascii=False)


SYSTEM_PROMPT = (
    "你是一位专业的旅行天气顾问。你的任务是根据用户提供的城市和出行日期，查询天气预报并给出旅行建议。\n"
    "工作流程：\n"
    "1. 查询目标城市的天气预报\n"
    "2. 分析出行日期范围内的天气情况\n"
    "3. 评估天气对旅行的影响\n"
    "4. 给出具体的穿衣和出行建议\n"
    "请以 JSON 格式返回最终结果，包含 forecasts（天气预报列表）、impact（影响评估）、suggestions（建议列表）字段。"
)

TOOLS = [weather_query_tool]


def create_weather_checker_agent():  # type: ignore[no-untyped-def]
    """构建天气查询 Agent（基于 LangGraph create_react_agent）。"""
    llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.1,
    )
    return create_react_agent(llm, TOOLS, prompt=SYSTEM_PROMPT)


async def check_weather(
    city: str,
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """天气查询入口：返回天气预报、影响评估和建议。"""
    graph = create_weather_checker_agent()
    query = (
        f"请查询 {city} 从 {start_date} 到 {end_date} 的天气预报，"
        "并评估天气对旅行的影响，给出穿衣和出行建议。"
        "请以 JSON 格式返回结果，包含 forecasts（天气预报列表）、impact（影响评估）、suggestions（建议列表）。"
    )

    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": query}]},
        config={"recursion_limit": 15},
    )
    output = result["messages"][-1].content
    try:
        return json.loads(output)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return {"raw_response": output}
