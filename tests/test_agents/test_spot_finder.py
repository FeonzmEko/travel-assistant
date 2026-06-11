"""景点搜索 Agent 单元测试"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agents.spot_finder import (
    TOOLS,
    PoiSearchInput,
    SpotDbSearchInput,
    amap_poi_search_tool,
    create_spot_finder_agent,
    find_spots,
)
from backend.services.amap import Spot

# --------------- Schema 验证 ---------------


class TestInputSchemas:
    def test_poi_search_input_required_fields(self):
        inp = PoiSearchInput(keyword="故宫", city="北京")
        assert inp.keyword == "故宫"
        assert inp.city == "北京"
        assert inp.type_code is None

    def test_poi_search_input_with_type_code(self):
        inp = PoiSearchInput(keyword="博物馆", city="上海", type_code="140000")
        assert inp.type_code == "140000"

    def test_spot_db_search_input(self):
        inp = SpotDbSearchInput(keyword="西湖", city="杭州")
        assert inp.keyword == "西湖"
        assert inp.city == "杭州"


# --------------- Tool 直接调用测试 ---------------


class TestAmapPoiSearchTool:
    @pytest.fixture
    def sample_spots(self) -> list[Spot]:
        return [
            Spot(
                name="故宫博物院",
                source_id="B000A8UIN8",
                city="北京",
                longitude=116.397026,
                latitude=39.918058,
                type_tags=["风景名胜", "博物馆"],
                address="东城区景山前街4号",
                tel="010-85007938",
            ),
        ]

    @patch("backend.agents.spot_finder.amap_poi_search", new_callable=AsyncMock)
    async def test_tool_returns_json(
        self, mock_search: AsyncMock, sample_spots: list[Spot]
    ):
        mock_search.return_value = sample_spots
        result = await amap_poi_search_tool.ainvoke({"keyword": "故宫", "city": "北京"})
        data = json.loads(result)
        assert len(data) == 1
        assert data[0]["name"] == "故宫博物院"
        assert data[0]["longitude"] == 116.397026
        mock_search.assert_awaited_once_with(
            keyword="故宫", city="北京", type_code=None
        )

    @patch("backend.agents.spot_finder.amap_poi_search", new_callable=AsyncMock)
    async def test_tool_empty_result(self, mock_search: AsyncMock):
        mock_search.return_value = []
        result = await amap_poi_search_tool.ainvoke(
            {"keyword": "不存在", "city": "火星"}
        )
        assert json.loads(result) == []


# --------------- Tool 注册验证 ---------------


class TestToolRegistration:
    def test_tools_list_has_two_tools(self):
        assert len(TOOLS) == 2
        names = [t.name for t in TOOLS]
        assert "amap_poi_search_tool" in names
        assert "spot_db_search_tool" in names


# --------------- Agent 构建测试 ---------------


class TestAgentBuild:
    @patch("backend.agents.spot_finder.settings")
    def testcreate_spot_finder_agent_returns_graph(self, mock_settings):
        mock_settings.deepseek_model = "deepseek-chat"
        mock_settings.deepseek_api_key = "test-key"
        mock_settings.deepseek_base_url = "https://api.test.com/v1"
        graph = create_spot_finder_agent()
        assert hasattr(graph, "ainvoke")


# --------------- find_spots 集成测试（Mock LLM） ---------------


class TestFindSpots:
    @patch("backend.agents.spot_finder.create_spot_finder_agent")
    async def test_find_spots_returns_list(self, mock_build):
        expected = [{"name": "故宫博物院", "city": "北京"}]
        mock_msg = MagicMock()
        mock_msg.content = json.dumps(expected, ensure_ascii=False)
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"messages": [mock_msg]}
        mock_build.return_value = mock_graph

        result = await find_spots(city="北京", keyword="故宫")
        assert result == expected
        mock_graph.ainvoke.assert_awaited_once()

    @patch("backend.agents.spot_finder.create_spot_finder_agent")
    async def test_find_spots_handles_non_json(self, mock_build):
        mock_msg = MagicMock()
        mock_msg.content = "无法解析的文本"
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"messages": [mock_msg]}
        mock_build.return_value = mock_graph

        result = await find_spots(city="北京")
        assert len(result) == 1
        assert "raw_response" in result[0]

    @patch("backend.agents.spot_finder.create_spot_finder_agent")
    async def test_find_spots_with_all_params(self, mock_build):
        mock_msg = MagicMock()
        mock_msg.content = "[]"
        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {"messages": [mock_msg]}
        mock_build.return_value = mock_graph

        result = await find_spots(
            city="杭州", keyword="西湖", type_code="110000", count=5
        )
        assert result == []
        call_args = mock_graph.ainvoke.call_args[0][0]
        user_msg = call_args["messages"][0]["content"]
        assert "杭州" in user_msg
        assert "西湖" in user_msg
