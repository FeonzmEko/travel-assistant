from datetime import datetime

from pydantic import BaseModel, Field


class SpotCacheCreate(BaseModel):
    source: str = Field(max_length=50)
    source_id: str = Field(max_length=100)
    name: str = Field(max_length=200)
    city: str = Field(max_length=50)
    longitude: float | None = None
    latitude: float | None = None
    type_tags: str | None = None
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
    description: str | None
    images: str | None
    rating: float | None
    open_time: str | None
    ticket_price: float | None
    review_summary: str | None
    cached_at: datetime

    model_config = {"from_attributes": True}
