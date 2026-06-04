"""规划 Agent 核心 — M6

接收用户旅游需求，通过 ReAct 推理调度子 Agent（景点搜索、路线规划、
天气查询、预算估算），汇总生成完整行程方案。
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import AIMessageChunk
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from backend.config import settings
from backend.services.amap import amap_poi_search, amap_route_plan
from backend.services.budget import budget_estimate
from backend.services.weather import weather_query

PLANNER_SYSTEM_PROMPT = """\
你是一位资深的旅游规划师，擅长为用户量身定制旅行方案。请用中文与用户交流。

## 核心原则：先了解需求，再做规划

你必须严格遵循"对话式规划"流程，绝对不要在用户第一次提问时就生成完整行程。

### 第一步：收集信息（必须！）
当用户提出旅游需求时，你需要先了解以下关键信息。如果用户没有提供，你必须主动询问：
1. **目的地**（如果用户已说明则跳过）
2. **出行日期**（具体哪几天？）
3. **出行人数**（几个人？有没有老人小孩？）
4. **交通方式**（自驾/高铁/飞机？）
5. **预算范围**（大概预算多少？）
6. **偏好**（喜欢自然风光还是人文历史？节奏紧凑还是休闲？有没有必去的景点？）

每个问题之间一定要换行，不要罗列在一起，根据用户已提供的信息灵活追问 2-3 个最关键的问题。

### 第二步：确认理解
当信息收集充分后，简要复述你对用户需求的理解，让用户确认。

### 第三步：调用工具并规划
用户确认后，再调用工具搜索景点、查天气、规划路线、估算预算，生成完整方案。

## 你的能力
你可以调用以下工具来收集信息：
- find_spots_tool：搜索目的地的旅游景点
- plan_route_tool：规划景点之间的交通路线
- check_weather_tool：查询目的地天气预报
- estimate_budget_tool：估算旅行预算

## 输出行程方案时的要求
- 用自然语言详细描述行程方案，包括每日安排、交通建议、美食推荐、注意事项
- 不要在回复中输出任何 JSON 代码。JSON 数据由系统自动生成，用户看不到也不需要看到
- 在回复的最末尾，单独附上 TripPlan JSON，用 ```json 代码块包裹（系统会自动提取并隐藏这部分）

## TripPlan JSON 格式（放在回复最末尾，系统自动提取）
```json
{
  "title": "行程标题",
  "destination": "目的地",
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "budget_total": 数字,
  "days": [
    {
      "day_index": 1,
      "date": "YYYY-MM-DD",
      "weather": "天气描述",
      "activities": [
        {
          "order_index": 1,
          "spot_name": "景点名称",
          "time_slot": "09:00-12:00",
          "transport": "步行/公交/地铁/打车",
          "notes": "游玩建议或备注",
          "estimated_cost": 数字
        }
      ]
    }
  ]
}
```

## 注意事项
- 每天安排 2-4 个景点，避免行程过于紧凑
- 考虑景点之间的距离和交通时间
- 根据天气情况灵活调整室内外活动
- 预算估算要包含交通、住宿、餐饮、门票等各项费用
"""

MAX_ITERATIONS = 25


# --------------- Tool Input Schemas ---------------

class PoiSearchInput(BaseModel):
    keyword: str = Field(description="搜索关键词")
    city: str = Field(description="城市名称")


class RouteInput(BaseModel):
    origin: str = Field(description="起点坐标 经度,纬度")
    destination: str = Field(description="终点坐标 经度,纬度")


class WeatherInput(BaseModel):
    city: str = Field(description="城市名称")


class BudgetInput(BaseModel):
    trip_days: int = Field(description="行程天数")
    ticket_prices: list[float] | None = Field(default=None, description="门票价格列表")
    budget_limit: float | None = Field(default=None, description="预算上限")


# --------------- Tools ---------------

@tool(args_schema=PoiSearchInput)
async def find_spots_tool(keyword: str, city: str) -> str:
    """搜索旅游景点，返回景点名称、坐标等信息。"""
    spots = await amap_poi_search(keyword, city)
    return json.dumps(
        [{"name": s.name, "id": s.source_id, "city": s.city,
          "lng": s.longitude, "lat": s.latitude}
         for s in spots[:10]],
        ensure_ascii=False,
    )


@tool(args_schema=RouteInput)
async def plan_route_tool(origin: str, destination: str) -> str:
    """规划两点之间的驾车路线，返回距离和时长。"""
    route = await amap_route_plan(origin, destination)
    return json.dumps(
        {"distance_km": route.distance / 1000, "duration_min": route.duration / 60},
        ensure_ascii=False,
    )


@tool(args_schema=WeatherInput)
async def check_weather_tool(city: str) -> str:
    """查询城市未来几天的天气预报。"""
    forecasts = await weather_query(city)
    return json.dumps(
        [{"date": f.date, "day": f.dayweather, "temp": f"{f.nighttemp}~{f.daytemp}℃"}
         for f in forecasts],
        ensure_ascii=False,
    )


@tool(args_schema=BudgetInput)
def estimate_budget_tool(
    trip_days: int,
    ticket_prices: list[float] | None = None,
    budget_limit: float | None = None,
) -> str:
    """估算旅行预算，包含住宿、餐饮、交通、门票等各项费用。"""
    result = budget_estimate(
        trip_days=trip_days, ticket_prices=ticket_prices, budget_limit=budget_limit
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


TOOLS = [find_spots_tool, plan_route_tool, check_weather_tool, estimate_budget_tool]


# --------------- Agent Construction ---------------

def create_planner_agent():  # type: ignore[no-untyped-def]
    """构建规划 Agent（基于 LangGraph create_react_agent）。"""
    llm = ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=0.3,
    )
    return create_react_agent(llm, TOOLS, prompt=PLANNER_SYSTEM_PROMPT)


# --------------- JSON Extraction ---------------

def extract_trip_plan(text: str) -> dict[str, Any] | None:
    """从 Agent 输出文本中提取 TripPlan JSON。

    尝试多种模式匹配，带降级方案：
    1. ```json ... ``` 代码块
    2. ``` ... ``` 代码块
    3. 以 {"title" 开头的独立 JSON 对象
    """
    patterns = [
        r"```json\s*(\{.*?\})\s*```",
        r"```\s*(\{.*?\})\s*```",
        r'(\{"title".*?\})\s*$',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))  # type: ignore[no-any-return]
            except json.JSONDecodeError:
                continue
    return None


def strip_trip_plan_json(text: str) -> str:
    """从文本中移除 TripPlan JSON 代码块，返回干净的显示文本。"""
    patterns = [
        r"```json\s*\{.*?\}\s*```",
        r"```\s*\{\"title\".*?\}\s*```",
    ]
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
    return cleaned


# --------------- Public API ---------------

async def plan_trip(
    user_input: str,
    history: list[dict[str, str]] | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """规划旅行方案（非流式），返回文本描述和结构化 TripPlan。

    Args:
        user_input: 用户输入的旅游需求
        history: 可选的对话历史 [{"role": "user"/"assistant", "content": "..."}]
        timeout: 超时时间（秒）

    Returns:
        {"text": str, "trip_plan": dict | None}
    """
    agent = create_planner_agent()

    messages: list[dict[str, str]] = []
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_input})

    try:
        result = await asyncio.wait_for(
            agent.ainvoke(
                {"messages": messages},
                config={"recursion_limit": MAX_ITERATIONS},
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return {"text": "抱歉，规划超时，请缩小需求范围后重试。", "trip_plan": None}

    agent_messages = result.get("messages", [])
    if not agent_messages:
        return {"text": "抱歉，无法生成行程方案。", "trip_plan": None}

    output = agent_messages[-1].content
    trip_plan = extract_trip_plan(output)
    return {"text": output, "trip_plan": trip_plan}


async def run_planner_stream(
    user_message: str,
    history: list[dict[str, str]] | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """流式规划旅行方案，逐步产出 SSE 事件。

    事件类型: thinking, token, tool_call, tool_result, trip_plan, done, error

    中间推理输出为 thinking 事件，最终回答为 token 事件。
    通过跟踪每段 LLM 输出和 tool 调用来判断：
    最后一段（后面没有 tool 调用的）LLM 输出才是 token。
    """
    agent = create_planner_agent()
    full_text = ""
    current_segment = ""
    pending_segments: list[str] = []

    messages: list[dict[str, str]] = []
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    collected_events: list[dict[str, Any]] = []

    try:
        async for event in agent.astream_events(
            {"messages": messages},
            config={"recursion_limit": MAX_ITERATIONS},
            version="v2",
        ):
            kind = event.get("event", "")

            if kind == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    current_segment += chunk.content
                    collected_events.append({"type": "_token", "data": chunk.content})

            elif kind == "on_tool_start":
                if current_segment.strip():
                    pending_segments.append(current_segment)
                    current_segment = ""
                tool_name = event.get("name", "")
                collected_events.append({"type": "tool_call", "data": {"tool": tool_name}})

            elif kind == "on_tool_end":
                tool_output = event.get("data", {}).get("output", "")
                collected_events.append({"type": "tool_result", "data": {"output": str(tool_output)[:500]}})

    except Exception as e:
        yield {"type": "error", "data": str(e)}
        return

    if current_segment.strip():
        pending_segments.append(current_segment)

    final_segment = pending_segments[-1] if pending_segments else ""
    thinking_segments = pending_segments[:-1] if len(pending_segments) > 1 else []
    full_text = final_segment

    if thinking_segments:
        yield {"type": "thinking", "data": "\n".join(s.strip() for s in thinking_segments)}

    for evt in collected_events:
        if evt["type"] == "tool_call":
            yield evt
        elif evt["type"] == "tool_result":
            yield evt

    trip_plan = extract_trip_plan(full_text)

    display_text = strip_trip_plan_json(full_text) if trip_plan else full_text

    for char_batch in _chunk_text(display_text, 20):
        yield {"type": "token", "data": char_batch}

    if trip_plan:
        yield {"type": "trip_plan", "data": trip_plan}

    yield {"type": "done", "data": {"text": display_text}}


def _chunk_text(text: str, size: int) -> list[str]:
    """将文本按固定大小分块，用于模拟流式输出。

    换行符单独作为一个 chunk 发送，避免被 SSE 协议当作行分隔符而丢失。
    """
    if not text:
        return []
    chunks: list[str] = []
    for line_idx, line in enumerate(text.split("\n")):
        if line_idx > 0:
            chunks.append("\n")
        if line:
            chunks.extend(line[i : i + size] for i in range(0, len(line), size))
    return chunks
