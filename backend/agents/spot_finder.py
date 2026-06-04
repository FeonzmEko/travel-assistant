"""景点搜索 Agent — M7

专门负责景点搜索与筛选，拥有独立的 LLM 推理能力。
可用工具：高德 POI 搜索、本地景点数据库检索。
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from backend.config import settings
from backend.services.amap import amap_poi_search


# --------------- Tool input schemas ---------------

class PoiSearchInput(BaseModel):
    keyword: str = Field(description="搜索关键词，如 '故宫' '美食'")
    city: str = Field(description="城市名称，如 '北京'")
    type_code: str | None = Field(default=None, description="高德 POI 类型编码，可选")


class SpotDbSearchInput(BaseModel):
    keyword: str = Field(description="搜索关键词")
    city: str = Field(description="城市名称")


# --------------- Tools ---------------

@tool(args_schema=PoiSearchInput)
async def amap_poi_search_tool(keyword: str, city: str, type_code: str | None = None) -> str:
    """通过高德地图 API 搜索景点 POI 信息，返回景点名称、地址、经纬度等。"""
    spots = await amap_poi_search(keyword=keyword, city=city, type_code=type_code)
    return json.dumps(
        [
            {
                "name": s.name,
                "source_id": s.source_id,
                "city": s.city,
                "longitude": s.longitude,
                "latitude": s.latitude,
                "type_tags": s.type_tags,
                "address": s.address,
                "tel": s.tel,
            }
            for s in spots
        ],
        ensure_ascii=False,
    )


@tool(args_schema=SpotDbSearchInput)
async def spot_db_search_tool(keyword: str, city: str) -> str:
    """从本地景点缓存数据库中搜索景点信息。"""
    from backend.database import async_session_factory
    from backend.crud.spot_cache import search_spots

    async with async_session_factory() as db:
        _total, items = await search_spots(db, keyword=keyword, city=city)
    return json.dumps(
        [
            {
                "name": i.name,
                "source_id": i.source_id,
                "city": i.city,
                "longitude": i.longitude,
                "latitude": i.latitude,
                "type_tags": i.type_tags,
            }
            for i in items
        ],
        ensure_ascii=False,
    )


SYSTEM_PROMPT = (
    "你是一位专业的景点搜索专家。你的任务是根据用户提供的城市和关键词，帮助他们找到最合适的旅游景点。\n"
    "工作流程：\n"
    "1. 首先尝试从本地缓存数据库搜索景点\n"
    "2. 如果本地结果不足，再调用高德地图 API 搜索\n"
    "3. 整合结果，去除重复，返回结构化的景点列表\n"
    "请以 JSON 数组格式返回最终结果，每个景点包含 name, source_id, city, longitude, latitude, type_tags, address 字段。"
)

TOOLS = [amap_poi_search_tool, spot_db_search_tool]


def create_spot_finder_agent():  # type: ignore[no-untyped-def]
    """构建景点搜索 Agent（基于 LangGraph create_react_agent）。"""
    llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.1,
    )
    return create_react_agent(llm, TOOLS, prompt=SYSTEM_PROMPT)


async def find_spots(
    city: str,
    keyword: str | None = None,
    type_code: str | None = None,
    count: int = 10,
) -> list[dict[str, Any]]:
    """景点搜索入口：返回结构化景点列表。"""
    graph = create_spot_finder_agent()
    query = f"请在{city}搜索"
    if keyword:
        query += f"与'{keyword}'相关的"
    if type_code:
        query += f"（类型编码 {type_code}）"
    query += f"景点，最多返回 {count} 个结果。"

    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": query}]},
        config={"recursion_limit": 15},
    )
    output = result["messages"][-1].content
    try:
        return json.loads(output)  # type: ignore[no-any-return]
    except json.JSONDecodeError:
        return [{"raw_response": output}]
