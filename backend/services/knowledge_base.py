"""Travel knowledge base backed by DashScope embeddings and Milvus."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.config import settings

SEED_DATA_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "travel_knowledge_seed.json"
)


class KnowledgeBaseError(RuntimeError):
    """Raised when the vector knowledge base cannot complete an operation."""


@dataclass(frozen=True)
class KnowledgeDocument:
    content: str
    category: str
    city: str = ""
    tags: tuple[str, ...] = ()
    source: str = "seed"
    doc_id: str | None = None

    @property
    def id(self) -> str:
        if self.doc_id:
            return self.doc_id
        raw = "|".join([self.category, self.city, self.source, self.content])
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class KnowledgeSearchResult:
    id: str
    content: str
    category: str
    city: str
    tags: list[str]
    source: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "category": self.category,
            "city": self.city,
            "tags": self.tags,
            "source": self.source,
            "score": self.score,
        }


class DashScopeEmbeddingClient:
    """Small async wrapper around Alibaba DashScope text embeddings."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return await asyncio.to_thread(self._embed_texts_sync, texts)

    def _embed_texts_sync(self, texts: list[str]) -> list[list[float]]:
        if not settings.dashscope_api_key:
            raise KnowledgeBaseError("缺少环境变量 DASHSCOPE_API_KEY")

        try:
            from dashscope import TextEmbedding
        except ImportError as exc:
            raise KnowledgeBaseError("缺少 dashscope 依赖，请先安装项目依赖") from exc

        response = TextEmbedding.call(
            api_key=settings.dashscope_api_key,
            model=settings.dashscope_embedding_model,
            input=texts,
            dimension=settings.embedding_dimension,
        )

        status_code = getattr(response, "status_code", 200)
        if status_code != 200:
            message = getattr(response, "message", "DashScope embedding 调用失败")
            raise KnowledgeBaseError(str(message))

        output = getattr(response, "output", None)
        if output is None and isinstance(response, dict):
            output = response.get("output")
        if not isinstance(output, dict):
            raise KnowledgeBaseError("DashScope embedding 响应格式异常")

        items = output.get("embeddings")
        if not isinstance(items, list):
            raise KnowledgeBaseError("DashScope embedding 响应缺少 embeddings")

        items.sort(key=lambda item: int(item.get("text_index", 0)))
        vectors = [item.get("embedding") for item in items]
        vector_count_mismatch = len(vectors) != len(texts)
        has_invalid_vector = not all(isinstance(v, list) for v in vectors)
        if vector_count_mismatch or has_invalid_vector:
            raise KnowledgeBaseError("DashScope embedding 数量与输入文本不一致")

        return [[float(value) for value in vector] for vector in vectors]


class MilvusKnowledgeBase:
    def __init__(
        self,
        embedding_client: DashScopeEmbeddingClient | None = None,
        collection_name: str | None = None,
    ) -> None:
        self.embedding_client = embedding_client or DashScopeEmbeddingClient()
        self.collection_name = collection_name or settings.milvus_collection_name
        self._alias = f"{self.collection_name}_alias"

    async def upsert_documents(self, docs: list[KnowledgeDocument]) -> int:
        if not docs:
            return 0
        vectors = await self.embedding_client.embed_texts([doc.content for doc in docs])
        return await asyncio.to_thread(self._insert_new_documents_sync, docs, vectors)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
        city: str | None = None,
    ) -> list[KnowledgeSearchResult]:
        query_vector = (await self.embedding_client.embed_texts([query]))[0]
        return await asyncio.to_thread(
            self._search_sync,
            query_vector,
            max(1, min(top_k, 10)),
            category,
            city,
        )

    def _connect(self) -> None:
        try:
            from pymilvus import connections
        except ImportError as exc:
            raise KnowledgeBaseError("缺少 pymilvus 依赖，请先安装项目依赖") from exc

        kwargs: dict[str, str] = {"alias": self._alias, "uri": settings.milvus_uri}
        if settings.milvus_token:
            kwargs["token"] = settings.milvus_token
        connections.connect(**kwargs)

    def _collection(self) -> Any:
        try:
            from pymilvus import (
                Collection,
                CollectionSchema,
                DataType,
                FieldSchema,
                utility,
            )
        except ImportError as exc:
            raise KnowledgeBaseError("缺少 pymilvus 依赖，请先安装项目依赖") from exc

        self._connect()
        if utility.has_collection(self.collection_name, using=self._alias):
            collection = Collection(self.collection_name, using=self._alias)
            collection.load()
            return collection

        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.VARCHAR,
                is_primary=True,
                max_length=64,
            ),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=4096),
            FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="city", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="tags", dtype=DataType.VARCHAR, max_length=512),
            FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=128),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=settings.embedding_dimension,
            ),
        ]
        schema = CollectionSchema(fields, description="旅游助手知识库")
        collection = Collection(self.collection_name, schema, using=self._alias)
        collection.create_index(
            field_name="embedding",
            index_params={"index_type": "FLAT", "metric_type": "COSINE", "params": {}},
        )
        collection.load()
        return collection

    def _insert_new_documents_sync(
        self,
        docs: list[KnowledgeDocument],
        vectors: list[list[float]],
    ) -> int:
        collection = self._collection()
        ids = [doc.id for doc in docs]
        existing_ids = self._existing_ids(collection, ids)

        rows = [
            (doc, vector)
            for doc, vector in zip(docs, vectors, strict=True)
            if doc.id not in existing_ids
        ]
        if not rows:
            return 0

        collection.insert(
            [
                [doc.id for doc, _vector in rows],
                [doc.content for doc, _vector in rows],
                [doc.category for doc, _vector in rows],
                [doc.city for doc, _vector in rows],
                [",".join(doc.tags) for doc, _vector in rows],
                [doc.source for doc, _vector in rows],
                [vector for _doc, vector in rows],
            ]
        )
        collection.flush()
        return len(rows)

    def _existing_ids(self, collection: Any, ids: list[str]) -> set[str]:
        if not ids:
            return set()
        escaped_ids = json.dumps(ids, ensure_ascii=False)
        rows = collection.query(expr=f"id in {escaped_ids}", output_fields=["id"])
        return {str(row["id"]) for row in rows}

    def _search_sync(
        self,
        query_vector: list[float],
        top_k: int,
        category: str | None,
        city: str | None,
    ) -> list[KnowledgeSearchResult]:
        collection = self._collection()
        search_results = collection.search(
            data=[query_vector],
            anns_field="embedding",
            param={"metric_type": "COSINE", "params": {}},
            limit=top_k,
            expr=self._build_filter(category=category, city=city),
            output_fields=["content", "category", "city", "tags", "source"],
        )

        results: list[KnowledgeSearchResult] = []
        for hit in search_results[0]:
            entity = getattr(hit, "entity", {})
            tags = str(self._entity_get(entity, "tags") or "")
            results.append(
                KnowledgeSearchResult(
                    id=str(getattr(hit, "id", "")),
                    content=str(self._entity_get(entity, "content") or ""),
                    category=str(self._entity_get(entity, "category") or ""),
                    city=str(self._entity_get(entity, "city") or ""),
                    tags=[tag for tag in tags.split(",") if tag],
                    source=str(self._entity_get(entity, "source") or ""),
                    score=self._hit_score(hit),
                )
            )
        return results

    def _build_filter(self, category: str | None, city: str | None) -> str | None:
        filters = []
        if category:
            filters.append(f'category == "{self._escape_expr(category)}"')
        if city:
            filters.append(f'city == "{self._escape_expr(city)}"')
        return " and ".join(filters) if filters else None

    @staticmethod
    def _escape_expr(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    @staticmethod
    def _entity_get(entity: Any, field: str) -> Any:
        if hasattr(entity, "get"):
            return entity.get(field)
        return entity[field]

    @staticmethod
    def _hit_score(hit: Any) -> float:
        return float(getattr(hit, "score", getattr(hit, "distance", 0.0)))


def load_seed_documents(path: Path = SEED_DATA_PATH) -> list[KnowledgeDocument]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    docs: list[KnowledgeDocument] = []
    for item in raw:
        docs.append(
            KnowledgeDocument(
                doc_id=item.get("id"),
                content=item["content"],
                category=item["category"],
                city=item.get("city", ""),
                tags=tuple(item.get("tags", [])),
                source=item.get("source", "seed"),
            )
        )
    return docs


_knowledge_base: MilvusKnowledgeBase | None = None


def get_knowledge_base() -> MilvusKnowledgeBase:
    global _knowledge_base
    if _knowledge_base is None:
        _knowledge_base = MilvusKnowledgeBase()
    return _knowledge_base


async def seed_travel_knowledge() -> int:
    return await get_knowledge_base().upsert_documents(load_seed_documents())


async def search_travel_knowledge(
    query: str,
    top_k: int = 5,
    category: str | None = None,
    city: str | None = None,
) -> list[dict[str, Any]]:
    results = await get_knowledge_base().search(
        query=query,
        top_k=top_k,
        category=category,
        city=city,
    )
    return [result.to_dict() for result in results]
