"""路线规划 Agent — M8

专门负责路线规划与交通方案推荐，拥有独立的 LLM 推理能力。
可用工具：高德路径规划 API。
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
from backend.services.amap import amap_route_plan


# --------------- Tool input schema ---------------

class RoutePlanInput(BaseModel):
    origin: str = Field(description="起点经纬度，格式 '经度,纬度'")
    destination: str = Field(description="终点经纬度，格式 '经度,纬度'")
    waypoints: list[str] | None = Field(default=None, description="途经点列表，每个格式 '经度,纬度'")
    strategy: int = Field(default=0, description="路线策略：0-速度优先，1-费用优先，2-距离优先")


# --------------- Tool ---------------

@tool(args_schema=RoutePlanInput)
async def amap_route_plan_tool(
    origin: str,
    destination: str,
    waypoints: list[str] | None = None,
    strategy: int = 0,
) -> str:
    """调用高德地图驾车路线规划 API，返回路线距离、时长和分段信息。"""
    route = await amap_route_plan(
        origin=origin, destination=destination, waypoints=waypoints, strategy=strategy
    )
    return json.dumps(asdict(route), ensure_ascii=False)


SYSTEM_PROMPT = (
    "你是一位专业的旅行路线规划师。你的任务是根据用户提供的景点列表和交通偏好，规划最优的游览路线。\n"
    "工作流程：\n"
    "1. 分析景点列表中各景点的位置（经纬度）\n"
    "2. 根据交通偏好选择合适的路线策略\n"
    "3. 调用路线规划工具获取详细路线\n"
    "4. 如果需要提供多条备选路线，请分别用不同策略（速度优先、费用优先、距离优先）调用路线规划工具\n"
    "5. 返回包含总距离、总时长和分段信息的路线方案\n"
    "请以 JSON 格式返回最终结果。"
)

TOOLS = [amap_route_plan_tool]


def create_route_planner_agent():  # type: ignore[no-untyped-def]
    """构建路线规划 Agent（基于 LangGraph create_react_agent）。"""
    llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.1,
    )
    return create_react_agent(llm, TOOLS, prompt=SYSTEM_PROMPT)


async def plan_route(
    spots: list[dict[str, Any]],
    transport_preference: str = "driving",
    multi_route: bool = False,
) -> dict[str, Any]:
    """路线规划入口：根据景点列表规划路线。

    Args:
        spots: 景点列表，每个包含 name, longitude, latitude
        transport_preference: 交通方式偏好
        multi_route: 是否返回多条备选路线

    Returns:
        路线规划结果，multi_route=True 时包含多条路线
    """
    graph = create_route_planner_agent()

    spots_desc = json.dumps(spots, ensure_ascii=False)
    query = (
        f"请根据以下景点列表规划游览路线，交通方式偏好为 {transport_preference}。\n"
        f"景点列表：{spots_desc}\n"
    )
    if multi_route:
        query += (
            "请分别使用速度优先（strategy=0）、费用优先（strategy=1）、距离优先（strategy=2）三种策略规划路线，"
            "返回 JSON 格式结果，包含 routes 数组，每条路线包含 strategy, distance_km, duration_min, steps 字段。"
        )
    else:
        query += "请依次规划相邻景点之间的路线，返回 JSON 格式结果。"

    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": query}]},
        config={"recursion_limit": 15},
    )
    output = result["messages"][-1].content
    try:
        return json.loads(output)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return {"raw_response": output}
