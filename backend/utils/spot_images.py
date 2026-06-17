"""景点图片相关工具：解析已存图片、生成兜底景色图。

兜底图片使用 LoremFlickr（按关键词返回真实风景照片，无需 API Key），
通过 lock 参数保证同一景点每次返回的图片稳定一致。前端还会在图片加载
失败时进一步降级到 Picsum 与本地 SVG，确保任何情况下都能显示画面。
"""

from __future__ import annotations

import hashlib
import json

DEFAULT_WIDTH = 600
DEFAULT_HEIGHT = 400

# 中文类型关键字 -> LoremFlickr 英文检索词，用于在没有具体图片时给出贴合主题的景色图
_TYPE_KEYWORDS: list[tuple[str, str]] = [
    ("湖", "lake,scenery"),
    ("山", "mountain,landscape"),
    ("海", "beach,sea"),
    ("园林", "garden,park"),
    ("公园", "park,nature"),
    ("寺", "temple,architecture"),
    ("庙", "temple,architecture"),
    ("塔", "pagoda,architecture"),
    ("博物", "museum"),
    ("动物", "wildlife,zoo"),
    ("古迹", "ancient,architecture"),
    ("古镇", "ancient,town"),
    ("街区", "old,street"),
    ("地标", "city,skyline"),
    ("美食", "food,cuisine"),
    ("餐", "food,restaurant"),
    ("小吃", "food,snack"),
    ("酒店", "hotel,resort"),
    ("住宿", "hotel,room"),
    ("购物", "shopping,mall"),
    ("风景", "landscape,scenery"),
    ("景点", "landmark,travel"),
]

_DEFAULT_KEYWORDS = "travel,china,landscape"


def _stable_lock(seed: str) -> int:
    """根据种子生成稳定的正整数，用于 LoremFlickr 的 lock 参数。"""
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    return int(digest, 16) % 100000


def _normalize_keywords(raw: str) -> str:
    """把空格分隔的检索词转换为 LoremFlickr 接受的逗号分隔形式。"""
    parts = [p for p in raw.replace(",", " ").split() if p]
    return ",".join(parts) if parts else _DEFAULT_KEYWORDS


def keywords_for(type_tags: str | None, query: str | None = None) -> str:
    """根据显式英文检索词或景点类型标签，推断一组图片检索关键词。"""
    if query:
        return _normalize_keywords(query)
    if type_tags:
        for marker, keywords in _TYPE_KEYWORDS:
            if marker in type_tags:
                return keywords
    return _DEFAULT_KEYWORDS


def fallback_images(
    name: str,
    type_tags: str | None = None,
    *,
    seed: str | None = None,
    query: str | None = None,
    count: int = 3,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
) -> list[str]:
    """生成一组稳定且贴合主题的兜底景色图 URL。"""
    keywords = keywords_for(type_tags, query)
    base_seed = seed or name or keywords
    return [
        f"https://loremflickr.com/{width}/{height}/{keywords}?lock="
        f"{_stable_lock(f'{base_seed}-{index}')}"
        for index in range(max(count, 1))
    ]


def fallback_image_url(
    name: str,
    type_tags: str | None = None,
    *,
    seed: str | None = None,
    query: str | None = None,
) -> str:
    """生成单张兜底景色图 URL。"""
    return fallback_images(name, type_tags, seed=seed, query=query, count=1)[0]


def parse_images(images: str | None) -> list[str]:
    """把数据库中存储的图片字段解析为 URL 列表。

    优先按 JSON 数组解析，兼容历史上以分号/换行分隔的旧数据。
    """
    if not images:
        return []
    text = images.strip()
    if not text:
        return []
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        data = None
    if isinstance(data, list):
        return [str(url).strip() for url in data if str(url).strip()]
    if isinstance(data, str) and data.strip():
        return [data.strip()]
    separators = ";" if ";" in text else "\n"
    return [part.strip() for part in text.split(separators) if part.strip()]


def serialize_images(urls: list[str] | None) -> str | None:
    """把图片 URL 列表序列化为数据库存储用的 JSON 字符串。"""
    cleaned = [u.strip() for u in (urls or []) if u and u.strip()]
    if not cleaned:
        return None
    return json.dumps(cleaned, ensure_ascii=False)
