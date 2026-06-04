"""路线规划 Agent — M8"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
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
    "4. 返回包含总距离、总时长和分段信息的路线方案\n"
    "请以 JSON 格式返回最终结果。"
)

TOOLS = [amap_route_plan_tool]


def _build_agent():
    llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )
    return create_agent(model=llm, tools=TOOLS, system_prompt=SYSTEM_PROMPT)


async def plan_route(
    spots: list[dict[str, Any]],
    transport_preference: str = "driving",
) -> dict[str, Any]:
    """路线规划入口：根据景点列表规划路线。"""
    graph = _build_agent()

    spots_desc = json.dumps(spots, ensure_ascii=False)
    query = (
        f"请根据以下景点列表规划游览路线，交通方式偏好为 {transport_preference}。\n"
        f"景点列表：{spots_desc}\n"
        "请依次规划相邻景点之间的路线，返回 JSON 格式结果。"
    )

    result = await graph.ainvoke({"messages": [{"role": "user", "content": query}]})
    output = result["messages"][-1].content
    try:
        return json.loads(output)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return {"raw_response": output}
