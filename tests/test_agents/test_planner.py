"""规划 Agent (M6) 测试

Mock 所有子 Agent Tool，验证调度逻辑、JSON 提取和流式输出。
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

from backend.agents.planner import (
    TOOLS,
    create_planner_agent,
    extract_trip_plan,
    plan_trip,
    run_planner_stream,
    search_travel_knowledge_tool,
)

SAMPLE_TRIP_JSON = {
    "title": "北京三日游",
    "destination": "北京",
    "start_date": "2025-07-01",
    "end_date": "2025-07-03",
    "budget_total": 3000,
    "days": [
        {
            "day_index": 1,
            "date": "2025-07-01",
            "weather": "晴",
            "activities": [
                {
                    "order_index": 1,
                    "spot_name": "故宫",
                    "time_slot": "09:00-12:00",
                    "transport": "地铁",
                    "notes": "提前预约",
                    "estimated_cost": 60,
                }
            ],
        }
    ],
}


# =================== extract_trip_plan 测试 ===================


class TestExtractTripPlan:
    def test_json_code_block(self) -> None:
        text = (
            "这是行程方案\n\n"
            "```json\n" + json.dumps(SAMPLE_TRIP_JSON, ensure_ascii=False) + "\n```"
        )
        plan = extract_trip_plan(text)
        assert plan is not None
        assert plan["title"] == "北京三日游"
        assert plan["destination"] == "北京"

    def test_plain_code_block(self) -> None:
        text = "方案如下\n```\n" + json.dumps(SAMPLE_TRIP_JSON) + "\n```"
        plan = extract_trip_plan(text)
        assert plan is not None
        assert plan["title"] == "北京三日游"

    def test_no_json(self) -> None:
        assert extract_trip_plan("这是一段普通文本，没有JSON") is None

    def test_invalid_json(self) -> None:
        assert extract_trip_plan("```json\n{invalid json}\n```") is None

    def test_json_with_surrounding_text(self) -> None:
        text = (
            "以下是为您规划的行程：\n\n"
            "北京是一座历史悠久的城市...\n\n"
            "```json\n"
            + json.dumps(SAMPLE_TRIP_JSON, ensure_ascii=False)
            + "\n```\n\n祝您旅途愉快！"
        )
        plan = extract_trip_plan(text)
        assert plan is not None
        assert plan["budget_total"] == 3000


# =================== Tool 注册测试 ===================


class TestToolRegistration:
    def test_tools_count(self) -> None:
        assert len(TOOLS) == 6

    def test_tool_names(self) -> None:
        names = {t.name for t in TOOLS}
        assert names == {
            "get_current_time_tool",
            "find_spots_agent",
            "plan_route_agent",
            "check_weather_agent",
            "estimate_budget_agent",
            "search_travel_knowledge_tool",
        }

    @patch("backend.services.knowledge_base.search_travel_knowledge", new_callable=AsyncMock)
    async def test_knowledge_tool_returns_json(self, mock_search: AsyncMock) -> None:
        mock_search.return_value = [
            {"content": "三亚经济型轿车淡季日租通常在 120-180 元"}
        ]

        result = await search_travel_knowledge_tool.ainvoke(
            {"query": "三亚租车价格", "city": "三亚", "category": "租车价格"}
        )

        data = json.loads(result)
        assert data[0]["content"].startswith("三亚经济型轿车")
        mock_search.assert_awaited_once_with(
            query="三亚租车价格",
            top_k=5,
            category="租车价格",
            city="三亚",
        )


# =================== Agent 构建测试 ===================


class TestCreatePlannerAgent:
    @patch("backend.agents.planner.settings")
    def test_build_returns_runnable(self, mock_settings: MagicMock) -> None:
        mock_settings.deepseek_model = "deepseek-chat"
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.deepseek_base_url = "https://api.test.com/v1"
        agent = create_planner_agent()
        assert hasattr(agent, "ainvoke")
        assert hasattr(agent, "astream_events")


# =================== plan_trip 测试 ===================


class TestPlanTrip:
    @patch("backend.agents.planner.create_planner_agent")
    async def test_returns_text_and_plan(self, mock_create: MagicMock) -> None:
        output_text = (
            "为您规划了北京三日游\n\n```json\n"
            + json.dumps(SAMPLE_TRIP_JSON, ensure_ascii=False)
            + "\n```"
        )
        mock_msg = MagicMock()
        mock_msg.content = output_text
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {"messages": [mock_msg]}
        mock_create.return_value = mock_agent

        result = await plan_trip("我想去北京玩三天")

        assert "text" in result
        assert result["trip_plan"] is not None
        assert result["trip_plan"]["title"] == "北京三日游"

    @patch("backend.agents.planner.create_planner_agent")
    async def test_no_json_in_output(self, mock_create: MagicMock) -> None:
        mock_msg = MagicMock()
        mock_msg.content = "抱歉，我无法为您规划行程。"
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {"messages": [mock_msg]}
        mock_create.return_value = mock_agent

        result = await plan_trip("我想去火星")

        assert result["trip_plan"] is None
        assert "text" in result

    @patch("backend.agents.planner.create_planner_agent")
    async def test_empty_messages(self, mock_create: MagicMock) -> None:
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {"messages": []}
        mock_create.return_value = mock_agent

        result = await plan_trip("你好")

        assert result["trip_plan"] is None
        assert "无法生成" in result["text"]

    @patch("backend.agents.planner.create_planner_agent")
    async def test_with_history(self, mock_create: MagicMock) -> None:
        mock_msg = MagicMock()
        mock_msg.content = "好的"
        mock_agent = AsyncMock()
        mock_agent.ainvoke.return_value = {"messages": [mock_msg]}
        mock_create.return_value = mock_agent

        history = [
            {"role": "user", "content": "我想去北京"},
            {"role": "assistant", "content": "好的，请问几天？"},
        ]
        await plan_trip("三天", history=history)

        call_args = mock_agent.ainvoke.call_args[0][0]
        assert len(call_args["messages"]) == 3
        assert call_args["messages"][0]["content"] == "我想去北京"

    @patch("backend.agents.planner.create_planner_agent")
    async def test_timeout_handling(self, mock_create: MagicMock) -> None:
        async def slow_invoke(*args, **kwargs):  # type: ignore[no-untyped-def]
            import asyncio

            await asyncio.sleep(10)

        mock_agent = MagicMock()
        mock_agent.ainvoke = slow_invoke
        mock_create.return_value = mock_agent

        result = await plan_trip("北京", timeout=0.1)
        assert "超时" in result["text"]
        assert result["trip_plan"] is None


# =================== run_planner_stream 测试 ===================


class TestRunPlannerStream:
    @patch("backend.agents.planner.create_planner_agent")
    async def test_stream_events_sequence(self, mock_create: MagicMock) -> None:
        trip_json = json.dumps(SAMPLE_TRIP_JSON, ensure_ascii=False)
        text_with_plan = f"行程如下\n```json\n{trip_json}\n```"

        async def fake_astream_events(inp, *, config=None, version=None):  # type: ignore[no-untyped-def]
            from langchain_core.messages import AIMessageChunk

            # 第一轮 LLM：工具调用轮次（含 tool_call_chunks）→ 应被过滤
            reasoning_chunk = AIMessageChunk(content="好的，让我搜索")
            reasoning_chunk.tool_call_chunks = [{"name": "find_spots_agent", "args": "{}", "id": "call_1", "index": 0, "type": "tool_call_chunk"}]
            yield {"event": "on_chat_model_start", "data": {}, "name": "ChatOpenAI"}
            yield {"event": "on_chat_model_stream", "data": {"chunk": reasoning_chunk}}
            yield {"event": "on_chat_model_end", "data": {}, "name": "ChatOpenAI"}

            # 工具执行
            yield {"event": "on_tool_start", "name": "find_spots_agent", "data": {}}
            yield {"event": "on_tool_end", "name": "find_spots_agent", "data": {"output": '[{"name":"故宫"}]'}}

            # 第二轮 LLM：最终回复（无 tool_call_chunks）→ 应被推送
            yield {"event": "on_chat_model_start", "data": {}, "name": "ChatOpenAI"}
            yield {"event": "on_chat_model_stream", "data": {"chunk": AIMessageChunk(content=text_with_plan)}}
            yield {"event": "on_chat_model_end", "data": {}, "name": "ChatOpenAI"}

        mock_agent = MagicMock()
        mock_agent.astream_events = fake_astream_events
        mock_create.return_value = mock_agent

        events = []
        async for evt in run_planner_stream("去北京"):
            events.append(evt)

        types = [e["type"] for e in events]
        assert "tool_call" in types
        assert "tool_result" in types
        assert "token" in types  # 最终回复轮次清洗后应生成 token 事件
        assert "trip_plan" in types
        assert types[-1] == "done"

        plan_event = next(e for e in events if e["type"] == "trip_plan")
        assert plan_event["data"]["title"] == "北京三日游"

        # token 事件中不应包含工具调用轮次的文本
        token_event = next(e for e in events if e["type"] == "token")
        assert "让我搜索" not in token_event["data"]

    @patch("backend.agents.planner.create_planner_agent")
    async def test_stream_no_plan(self, mock_create: MagicMock) -> None:
        from langchain_core.messages import AIMessageChunk

        async def fake_astream_events(inp, *, config=None, version=None):  # type: ignore[no-untyped-def]
            yield {"event": "on_chat_model_start", "data": {}, "name": "ChatOpenAI"}
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": AIMessageChunk(content="随便说点什么")},
            }
            yield {"event": "on_chat_model_end", "data": {}, "name": "ChatOpenAI"}

        mock_agent = MagicMock()
        mock_agent.astream_events = fake_astream_events
        mock_create.return_value = mock_agent

        events = []
        async for evt in run_planner_stream("你好"):
            events.append(evt)

        types = [e["type"] for e in events]
        assert "trip_plan" not in types
        assert "token" in types  # 简单对话（无工具调用）应有 token
        assert "done" in types

    @patch("backend.agents.planner.create_planner_agent")
    async def test_stream_error_handling(self, mock_create: MagicMock) -> None:
        async def failing_stream(inp, *, config=None, version=None):  # type: ignore[no-untyped-def]
            raise RuntimeError("LLM API error")
            yield  # make it an async generator (unreachable, but needed for syntax)

        mock_agent = MagicMock()
        mock_agent.astream_events = failing_stream
        mock_create.return_value = mock_agent

        events = []
        async for evt in run_planner_stream("北京"):
            events.append(evt)

        assert any(e["type"] == "error" for e in events)
