"""规划 Agent 核心 — M6

作为顶层调度者，通过 ReAct 推理调度子 Agent（景点搜索、路线规划、
天气查询、预算估算），每个子 Agent 拥有独立的 LLM 推理能力和专属工具。
Planner 负责需求拆解、子任务调度和结果汇总。
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from typing import Any

from langchain_core.messages import AIMessageChunk
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel, Field

from backend.config import settings

PLANNER_SYSTEM_PROMPT = """\
你是一位资深的旅游规划师，擅长为用户量身定制旅行方案。请用中文与用户交流。

## 架构说明
你是规划 Agent（Planner），负责接收用户需求、拆解子任务，并调度以下子 Agent：
- **景点搜索 Agent**（find_spots_agent）：搜索和筛选景点信息
- **路线规划 Agent**（plan_route_agent）：规划最优游览路线和交通方式
- **天气查询 Agent**（check_weather_agent）：查询天气预报并评估影响
- **预算估算 Agent**（estimate_budget_agent）：估算行程费用

每个子 Agent 拥有独立的 LLM 推理能力和专属工具，你只需要将任务分发给它们。

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

### 第三步：调度子 Agent 并规划
用户确认后，按以下流程调度子 Agent：
1. 先调用 get_current_time_tool 获取当前日期
2. 调用 find_spots_agent 搜索目的地景点
3. 调用 check_weather_agent 查询天气
4. 根据景点信息调用 plan_route_agent 规划路线
5. 调用 estimate_budget_agent 估算预算
6. 汇总所有子 Agent 的结果，生成完整行程方案

### 行程调整（P-02）
当用户要求修改已生成的行程时：
- 理解用户的修改意图（增减景点、调整顺序、更换日期等）
- 仅针对变更部分重新调用相关子 Agent
- 保留未变更部分，在原行程基础上增量修改
- 重新生成完整的 TripPlan JSON

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
  "budget_breakdown": "住宿:X元,餐饮:X元,交通:X元,门票:X元",
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
          "estimated_cost": 数字,
          "longitude": 经度数字,
          "latitude": 纬度数字
        }
      ]
    }
  ]
}
```

## 注意事项
- 每天安排 2-4 个景点，避免行程过于紧凑
- 考虑景点之间的距离和交通时间
- 每个活动尽量从景点搜索结果中带上 longitude 和 latitude，便于前端展示路线地图
- 根据天气情况灵活调整室内外活动
- 预算估算要包含交通、住宿、餐饮、门票等各项费用
- budget_breakdown 字段务必填写费用分类明细
"""

MAX_ITERATIONS = 25


# --------------- Sub-Agent Tool Input Schemas ---------------

class FindSpotsInput(BaseModel):
    city: str = Field(description="城市名称")
    keyword: str = Field(default="景点", description="搜索关键词")


class PlanRouteInput(BaseModel):
    spots_json: str = Field(description="景点列表 JSON 字符串，每个景点包含 name, longitude, latitude")
    transport_preference: str = Field(default="driving", description="交通方式偏好")
    multi_route: bool = Field(default=False, description="是否返回多条备选路线进行对比")


class CheckWeatherInput(BaseModel):
    city: str = Field(description="城市名称")
    start_date: str = Field(description="开始日期 YYYY-MM-DD")
    end_date: str = Field(description="结束日期 YYYY-MM-DD")


class EstimateBudgetInput(BaseModel):
    trip_days: int = Field(description="行程天数")
    ticket_prices: list[float] | None = Field(default=None, description="门票价格列表")
    transport_mode: str = Field(default="public", description="交通方式：public 或 taxi")
    budget_limit: float | None = Field(default=None, description="预算上限")


# --------------- Sub-Agent Tools ---------------
# 每个工具内部调用对应的子 Agent，子 Agent 拥有独立的 LLM 推理能力

@tool(args_schema=FindSpotsInput)
async def find_spots_agent(city: str, keyword: str = "景点") -> str:
    """调用景点搜索 Agent：搜索指定城市的旅游景点，返回结构化景点列表。
    景点 Agent 会自动搜索本地数据库和高德地图 API，并整合去重。"""
    from backend.agents.spot_finder import find_spots
    try:
        spots = await find_spots(city=city, keyword=keyword)
        return json.dumps(spots, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"景点搜索 Agent 执行失败: {e}"}, ensure_ascii=False)


@tool(args_schema=PlanRouteInput)
async def plan_route_agent(
    spots_json: str,
    transport_preference: str = "driving",
    multi_route: bool = False,
) -> str:
    """调用路线规划 Agent：根据景点列表规划游览路线。
    路线 Agent 会调用高德路线规划 API 计算最优路线。
    设置 multi_route=true 可获得多条备选路线进行对比。"""
    from backend.agents.route_planner import plan_route
    try:
        spots = json.loads(spots_json)
        result = await plan_route(
            spots=spots,
            transport_preference=transport_preference,
            multi_route=multi_route,
        )
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"路线规划 Agent 执行失败: {e}"}, ensure_ascii=False)


@tool(args_schema=CheckWeatherInput)
async def check_weather_agent(city: str, start_date: str, end_date: str) -> str:
    """调用天气查询 Agent：查询目的地天气预报并评估对旅行的影响。
    天气 Agent 会查询天气 API 并给出穿衣和出行建议。"""
    from backend.agents.weather_checker import check_weather
    try:
        result = await check_weather(city=city, start_date=start_date, end_date=end_date)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"天气查询 Agent 执行失败: {e}"}, ensure_ascii=False)


@tool(args_schema=EstimateBudgetInput)
async def estimate_budget_agent(
    trip_days: int,
    ticket_prices: list[float] | None = None,
    transport_mode: str = "public",
    budget_limit: float | None = None,
) -> str:
    """调用预算估算 Agent：估算旅行预算，包含住宿、餐饮、交通、门票等各项费用。
    预算 Agent 会计算费用明细并给出预算建议。"""
    from backend.agents.budget_estimator import estimate_trip_budget
    try:
        result = await estimate_trip_budget(
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
    except Exception as e:
        return json.dumps({"error": f"预算估算 Agent 执行失败: {e}"}, ensure_ascii=False)


@tool
def get_current_time_tool() -> str:
    """获取当前的确切日期和时间（北京时间），用于确定用户所说的"最近""这周末"等相对时间。"""
    tz_cn = timezone(timedelta(hours=8))
    now = datetime.now(tz_cn)
    weekday_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    return json.dumps({
        "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": weekday_names[now.weekday()],
        "timestamp": int(now.timestamp()),
    }, ensure_ascii=False)


TOOLS = [
    get_current_time_tool,
    find_spots_agent,
    plan_route_agent,
    check_weather_agent,
    estimate_budget_agent,
]


# --------------- Agent Construction ---------------

def create_planner_agent():  # type: ignore[no-untyped-def]
    """构建规划 Agent（基于 LangGraph create_react_agent）。

    Planner Agent 通过调用子 Agent Tool 来完成任务，
    每个子 Agent 内部拥有独立的 LLM 推理能力和专属工具。
    """
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
    """规划旅行方案（非流式），返回文本描述和结构化 TripPlan。"""
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
    """将文本按固定大小分块，用于模拟流式输出。"""
    if not text:
        return []
    chunks: list[str] = []
    for line_idx, line in enumerate(text.split("\n")):
        if line_idx > 0:
            chunks.append("\n")
        if line:
            chunks.extend(line[i : i + size] for i in range(0, len(line), size))
    return chunks
