"""天气查询 Agent 单元测试"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agents.weather_checker import (
    WeatherQueryInput,
    weather_query_tool,
    check_weather,
    _build_agent,
    TOOLS,
)
from backend.services.weather import WeatherForecast


# --------------- Schema 验证 ---------------

class TestInputSchema:
    def test_weather_query_input(self):
        inp = WeatherQueryInput(city="北京")
        assert inp.city == "北京"


# --------------- Tool 直接调用测试 ---------------

class TestWeatherQueryTool:
    @pytest.fixture
    def sample_forecasts(self) -> list[WeatherForecast]:
        return [
            WeatherForecast(
                date="2025-06-01",
                dayweather="晴",
                nightweather="多云",
                daytemp="32",
                nighttemp="22",
                daywind="南",
                nightwind="南",
                daypower="≤3",
                nightpower="≤3",
            ),
            WeatherForecast(
                date="2025-06-02",
                dayweather="阴",
                nightweather="小雨",
                daytemp="28",
                nighttemp="20",
                daywind="东",
                nightwind="东",
                daypower="4-5",
                nightpower="4-5",
            ),
        ]

    @patch("backend.agents.weather_checker.weather_query", new_callable=AsyncMock)
    async def test_tool_returns_json(
        self, mock_query: AsyncMock, sample_forecasts: list[WeatherForecast]
    ):
        mock_query.return_value = sample_forecasts
        result = await weather_query_tool.ainvoke({"city": "北京"})
        data = json.loads(result)
        assert len(data) == 2
        assert data[0]["dayweather"] == "晴"
        assert data[1]["date"] == "2025-06-02"

    @patch("backend.agents.weather_checker.weather_query", new_callable=AsyncMock)
    async def test_tool_empty_result(self, mock_query: AsyncMock):
        mock_query.return_value = []
        result = await weather_query_tool.ainvoke({"city": "未知城市"})
        assert json.loads(result) == []


# --------------- Tool 注册验证 ---------------

class TestToolRegistration:
    def test_tools_list(self):
        assert len(TOOLS) == 1
        assert TOOLS[0].name == "weather_query_tool"


# --------------- Agent 构建测试 ---------------

class TestAgentBuild:
    @patch("backend.agents.weather_checker.settings")
    def test_build_agent_returns_graph(self, mock_settings):
        mock_settings.deepseek_model = "deepseek-chat"
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.deepseek_base_url = "https://api.test.com/v1"
        graph = _build_agent()
        assert hasattr(graph, "ainvoke")


# --------------- check_weather 集成测试（Mock LLM） ---------------

class TestCheckWeather:
    @patch("backend.agents.weather_checker._build_agent")
    async def test_check_weather_returns_dict(self, mock_build):
        expected = {
            "forecasts": [{"date": "2025-06-01", "dayweather": "晴"}],
            "impact": "天气良好，适合出行",
            "suggestions": ["建议携带防晒用品", "注意防暑降温"],
        }
        mock_msg = MagicMock()
        mock_msg.content = json.dumps(expected, ensure_ascii=False)
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"messages": [mock_msg]}
        mock_build.return_value = mock_graph

        result = await check_weather(city="北京", start_date="2025-06-01", end_date="2025-06-03")
        assert result == expected
        call_args = mock_graph.ainvoke.call_args[0][0]
        user_msg = call_args["messages"][0]["content"]
        assert "北京" in user_msg
        assert "2025-06-01" in user_msg

    @patch("backend.agents.weather_checker._build_agent")
    async def test_check_weather_handles_non_json(self, mock_build):
        mock_msg = MagicMock()
        mock_msg.content = "天气查询异常"
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"messages": [mock_msg]}
        mock_build.return_value = mock_graph

        result = await check_weather(city="北京", start_date="2025-06-01", end_date="2025-06-02")
        assert "raw_response" in result
