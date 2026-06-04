from datetime import datetime

from sqlalchemy import Float, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SpotCache(Base):
    __tablename__ = "spot_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50))
    source_id: Mapped[str] = mapped_column(String(100), index=True)
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(50))
    longitude: Mapped[float | None] = mapped_column(Float, default=None)
    latitude: Mapped[float | None] = mapped_column(Float, default=None)
    type_tags: Mapped[str | None] = mapped_column(Text, default=None)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    images: Mapped[str | None] = mapped_column(Text, default=None)
    rating: Mapped[float | None] = mapped_column(Float, default=None)
    open_time: Mapped[str | None] = mapped_column(String(200), default=None)
    ticket_price: Mapped[float | None] = mapped_column(Float, default=None)
    review_summary: Mapped[str | None] = mapped_column(Text, default=None)
    cached_at: Mapped[datetime] = mapped_column(server_default=func.now())
