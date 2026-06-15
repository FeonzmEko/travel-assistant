from __future__ import annotations

from backend.services.knowledge_base import (
    DashScopeEmbeddingClient,
    KnowledgeDocument,
    KnowledgeSearchResult,
    MilvusKnowledgeBase,
    load_seed_documents,
)


class FakeEmbeddingClient(DashScopeEmbeddingClient):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0, 0.0] for _text in texts]


class FakeKnowledgeBase(MilvusKnowledgeBase):
    def __init__(self) -> None:
        super().__init__(embedding_client=FakeEmbeddingClient())
        self.inserted_vectors: list[list[float]] = []

    def _insert_new_documents_sync(
        self,
        docs: list[KnowledgeDocument],
        vectors: list[list[float]],
    ) -> int:
        self.inserted_vectors = vectors
        return len(docs)

    def _search_sync(
        self,
        query_vector: list[float],
        top_k: int,
        category: str | None,
        city: str | None,
    ) -> list[KnowledgeSearchResult]:
        return [
            KnowledgeSearchResult(
                id="doc-1",
                content="杭州九溪到龙井村适合轻徒步",
                category=category or "小众路线",
                city=city or "杭州",
                tags=["徒步"],
                source="test",
                score=query_vector[0],
            )
        ][:top_k]


def test_knowledge_document_id_is_deterministic() -> None:
    doc = KnowledgeDocument(content="三亚租车价格参考", category="租车价格", city="三亚")
    same_doc = KnowledgeDocument(
        content="三亚租车价格参考",
        category="租车价格",
        city="三亚",
    )

    assert doc.id == same_doc.id
    assert len(doc.id) == 40


def test_load_seed_documents() -> None:
    docs = load_seed_documents()

    assert docs
    assert {doc.category for doc in docs} >= {"租车价格", "小众路线"}


async def test_upsert_documents_embeds_content() -> None:
    kb = FakeKnowledgeBase()
    inserted = await kb.upsert_documents(
        [KnowledgeDocument(content="大理 SUV 日租参考", category="租车价格")]
    )

    assert inserted == 1
    assert kb.inserted_vectors == [[1.0, 0.0, 0.0]]


async def test_search_returns_dict_ready_result() -> None:
    kb = FakeKnowledgeBase()
    results = await kb.search(query="杭州小众路线", city="杭州", category="小众路线")

    assert results[0].to_dict()["city"] == "杭州"
    assert results[0].score == 1.0
