"""Knowledge base management and query API."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from backend.api.deps import get_current_user
from backend.models.user import User
from backend.services.knowledge_base import (
    KnowledgeBaseError,
    search_travel_knowledge,
    seed_travel_knowledge,
)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


class KnowledgeSeedResponse(BaseModel):
    inserted: int


class KnowledgeQueryRequest(BaseModel):
    query: str = Field(description="自然语言查询，如：三亚租车价格")
    top_k: int = Field(default=5, ge=1, le=10)
    category: str | None = Field(default=None, description="可选分类过滤")
    city: str | None = Field(default=None, description="可选城市过滤")


class KnowledgeQueryResponse(BaseModel):
    results: list[dict[str, object]]


@router.post("/seed", response_model=KnowledgeSeedResponse)
async def seed_knowledge(
    current_user: User = Depends(get_current_user),
) -> KnowledgeSeedResponse:
    _ = current_user
    try:
        inserted = await seed_travel_knowledge()
    except KnowledgeBaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return KnowledgeSeedResponse(inserted=inserted)


@router.post("/query", response_model=KnowledgeQueryResponse)
async def query_knowledge(
    request: KnowledgeQueryRequest,
    current_user: User = Depends(get_current_user),
) -> KnowledgeQueryResponse:
    _ = current_user
    try:
        results = await search_travel_knowledge(
            query=request.query,
            top_k=request.top_k,
            category=request.category,
            city=request.city,
        )
    except KnowledgeBaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return KnowledgeQueryResponse(results=results)
