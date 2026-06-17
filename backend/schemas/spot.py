from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, model_validator

from backend.utils.spot_images import fallback_images, parse_images


class SpotCacheCreate(BaseModel):
    source: str = Field(max_length=50)
    source_id: str = Field(max_length=100)
    name: str = Field(max_length=200)
    city: str = Field(max_length=50)
    longitude: float | None = None
    latitude: float | None = None
    type_tags: str | None = None
    address: str | None = None
    tel: str | None = None
    description: str | None = None
    images: str | None = None
    rating: float | None = None
    open_time: str | None = None
    ticket_price: float | None = None
    review_summary: str | None = None


class SpotCacheUpdate(BaseModel):
    description: str | None = None
    images: str | None = None
    rating: float | None = None
    open_time: str | None = None
    ticket_price: float | None = None
    address: str | None = None
    tel: str | None = None
    review_summary: str | None = None


class SpotCacheOut(BaseModel):
    id: int
    source: str
    source_id: str
    name: str
    city: str
    longitude: float | None
    latitude: float | None
    type_tags: str | None
    address: str | None = None
    tel: str | None = None
    description: str | None
    images: str | None = Field(default=None, exclude=True)
    rating: float | None
    open_time: str | None
    ticket_price: float | None
    review_summary: str | None
    cached_at: datetime

    # 派生字段：对齐前端契约，由 _populate_derived 自动填充
    image_url: str = ""
    images_list: list[str] = Field(default_factory=list)
    type: str | None = None

    model_config = {"from_attributes": True}

    @model_validator(mode="after")
    def _populate_derived(self) -> Self:
        """根据已存图片或类型生成主图、图集与前端 type 字段。"""
        urls = parse_images(self.images)
        if not urls:
            urls = fallback_images(self.name, self.type_tags, seed=self.source_id)
        self.images_list = urls
        self.image_url = urls[0] if urls else ""
        self.type = self.type_tags
        return self
