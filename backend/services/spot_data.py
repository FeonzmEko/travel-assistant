"""精选景点数据：作为高德 POI 不可用时的兜底数据源。

当未配置可用的高德 Web 服务 Key（或高德返回为空）时，搜索接口会回退到
这份内置的热门景点数据，保证用户搜索后仍能看到带图片与详情的结果。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "spots_seed.json"


@lru_cache(maxsize=1)
def _load_curated_spots() -> list[dict[str, Any]]:
    if not _DATA_FILE.exists():
        return []
    with _DATA_FILE.open("r", encoding="utf-8") as fp:
        data = json.load(fp)
    return data if isinstance(data, list) else []


def _matches(
    spot: dict[str, Any],
    keyword: str | None,
    city: str | None,
    type_tag: str | None,
) -> bool:
    name = spot.get("name", "")
    spot_city = spot.get("city", "")
    tags = spot.get("type_tags", []) or []
    description = spot.get("description", "")

    if city:
        if city not in spot_city and spot_city not in city:
            return False

    if type_tag and not any(type_tag in tag for tag in tags):
        return False

    if keyword:
        haystack = [name, spot_city, description, *tags]
        if not any(keyword in field for field in haystack):
            return False

    return True


def search_curated_spots(
    keyword: str | None = None,
    city: str | None = None,
    type_tag: str | None = None,
) -> list[dict[str, Any]]:
    """根据关键词/城市/类型筛选精选景点。"""
    return [
        spot
        for spot in _load_curated_spots()
        if _matches(spot, keyword, city, type_tag)
    ]
