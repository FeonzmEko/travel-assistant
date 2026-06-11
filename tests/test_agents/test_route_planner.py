"""路线规划 Agent 单元测试"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agents.route_planner import (
    TOOLS,
    RoutePlanInput,
    amap_route_plan_tool,
    create_route_planner_agent,
    plan_route,
)
from backend.services.amap import Route, RouteSegment

# --------------- Schema 验证 ---------------


class TestInputSchema:
    def test_route_plan_input_defaults(self):
        inp = RoutePlanInput(origin="116.397,39.918", destination="116.487,39.998")
        assert inp.waypoints is None
        assert inp.strategy == 0

    def test_route_plan_input_full(self):
        inp = RoutePlanInput(
            origin="116.397,39.918",
            destination="116.487,39.998",
            waypoints=["116.45,39.95"],
            strategy=1,
        )
        assert len(inp.waypoints) == 1
        assert inp.strategy == 1


# --------------- Tool 直接调用测试 ---------------


class TestAmapRoutePlanTool:
    @pytest.fixture
    def sample_route(self) -> Route:
        return Route(
            distance=12500.0,
            duration=1800.0,
            segments=[
                RouteSegment(
                    origin="116.397,39.918",
                    destination="116.487,39.998",
                    distance=12500.0,
                    duration=1800.0,
                    steps=["沿长安街向东行驶"],
                )
            ],
        )

    @patch("backend.agents.route_planner.amap_route_plan", new_callable=AsyncMock)
    async def test_tool_returns_json(self, mock_plan: AsyncMock, sample_route: Route):
        mock_plan.return_value = sample_route
        result = await amap_route_plan_tool.ainvoke(
            {"origin": "116.397,39.918", "destination": "116.487,39.998"}
        )
        data = json.loads(result)
        assert data["distance"] == 12500.0
        assert data["duration"] == 1800.0
        assert len(data["segments"]) == 1

    @patch("backend.agents.route_planner.amap_route_plan", new_callable=AsyncMock)
    async def test_tool_empty_route(self, mock_plan: AsyncMock):
        mock_plan.return_value = Route(distance=0, duration=0)
        result = await amap_route_plan_tool.ainvoke(
            {"origin": "0,0", "destination": "0,0"}
        )
        data = json.loads(result)
        assert data["distance"] == 0
        assert data["segments"] == []


# --------------- Tool 注册验证 ---------------


class TestToolRegistration:
    def test_tools_list(self):
        assert len(TOOLS) == 1
        assert TOOLS[0].name == "amap_route_plan_tool"


# --------------- Agent 构建测试 ---------------


class TestAgentBuild:
    @patch("backend.agents.route_planner.settings")
    def testcreate_route_planner_agent_returns_graph(self, mock_settings):
        mock_settings.deepseek_model = "deepseek-chat"
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.deepseek_base_url = "https://api.test.com/v1"
        graph = create_route_planner_agent()
        assert hasattr(graph, "ainvoke")


# --------------- plan_route 集成测试（Mock LLM） ---------------


class TestPlanRoute:
    @pytest.fixture
    def sample_spots(self) -> list[dict]:
        return [
            {"name": "故宫", "longitude": 116.397, "latitude": 39.918},
            {"name": "天坛", "longitude": 116.410, "latitude": 39.882},
        ]

    @patch("backend.agents.route_planner.create_route_planner_agent")
    async def test_plan_route_returns_dict(self, mock_build, sample_spots):
        expected = {
            "distance": 5000,
            "duration": 900,
            "segments": [{"origin": "故宫", "destination": "天坛"}],
        }
        mock_msg = MagicMock()
        mock_msg.content = json.dumps(expected, ensure_ascii=False)
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"messages": [mock_msg]}
        mock_build.return_value = mock_graph

        result = await plan_route(spots=sample_spots)
        assert result == expected

    @patch("backend.agents.route_planner.create_route_planner_agent")
    async def test_plan_route_handles_non_json(self, mock_build, sample_spots):
        mock_msg = MagicMock()
        mock_msg.content = "路线规划失败"
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"messages": [mock_msg]}
        mock_build.return_value = mock_graph

        result = await plan_route(spots=sample_spots)
        assert "raw_response" in result

    @patch("backend.agents.route_planner.create_route_planner_agent")
    async def test_plan_route_with_transport_preference(self, mock_build, sample_spots):
        mock_msg = MagicMock()
        mock_msg.content = "{}"
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"messages": [mock_msg]}
        mock_build.return_value = mock_graph

        await plan_route(spots=sample_spots, transport_preference="public")
        call_args = mock_graph.ainvoke.call_args[0][0]
        user_msg = call_args["messages"][0]["content"]
        assert "public" in user_msg
