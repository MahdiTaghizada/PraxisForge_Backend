from __future__ import annotations

import uuid
import logging

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    HasIdCondition,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from src.application.interfaces.embedding import EmbeddingService
from src.application.interfaces.vector_store import (
    VectorChunk,
    VectorSearchResult,
    VectorStoreService,
)
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)

# Gemini text-embedding-004 outputs 768-dimensional vectors
_VECTOR_SIZE = 768


class QdrantVectorStore(VectorStoreService):
    """Concrete vector store implementation backed by Qdrant + Gemini embeddings."""

    def __init__(self, embedding_service: EmbeddingService) -> None:
        self._client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        self._collection = settings.qdrant_collection
        self._embedding = embedding_service

    # ── Collection management ─────────────────────────────

    async def ensure_collection(self) -> None:
        """Create the Qdrant collection and payload indexes if they do not exist."""
        collections = self._client.get_collections().collections
        existing_names = {c.name for c in collections}

        if self._collection not in existing_names:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=_VECTOR_SIZE,
                    distance=Distance.COSINE,
                ),
            )
            logger.info("Created Qdrant collection '%s'", self._collection)

        # Payload indexes for efficient multi-tenant filtering
        self._client.create_payload_index(
            collection_name=self._collection,
            field_name="project_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        self._client.create_payload_index(
            collection_name=self._collection,
            field_name="chunk_type",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        self._client.create_payload_index(
            collection_name=self._collection,
            field_name="file_id",
            field_schema=PayloadSchemaType.KEYWORD,
        )

    # ── Upsert ────────────────────────────────────────────

    async def upsert_chunks(self, chunks: list[VectorChunk]) -> None:
        if not chunks:
            return

        texts = [c.text for c in chunks]
        vectors = await self._embedding.embed_texts(texts)

        points: list[PointStruct] = []
        for chunk, vector in zip(chunks, vectors):
            point_id = str(uuid.uuid4())
            payload = {
                "text": chunk.text,
                "project_id": str(chunk.project_id),
                "chunk_type": chunk.chunk_type,
            }
            if chunk.file_id is not None:
                payload["file_id"] = str(chunk.file_id)
            if chunk.metadata:
                payload["extra"] = chunk.metadata
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        self._client.upsert(collection_name=self._collection, points=points)
        logger.info("Upserted %d chunks into Qdrant", len(points))

    # ── Search ────────────────────────────────────────────

    async def search(
        self,
        query: str,
        project_id: uuid.UUID,
        limit: int = 5,
        chunk_type: str | None = None,
    ) -> list[VectorSearchResult]:
        query_vector = await self._embedding.embed_query(query)

        must_conditions = [
            FieldCondition(key="project_id", match=MatchValue(value=str(project_id)))
        ]
        if chunk_type:
            must_conditions.append(
                FieldCondition(key="chunk_type", match=MatchValue(value=chunk_type))
            )

        results = self._client.query_points(
            collection_name=self._collection,
            query=query_vector,
            query_filter=Filter(must=must_conditions),
            limit=limit,
            with_payload=True,
        )

        return [
            VectorSearchResult(
                text=hit.payload.get("text", ""),
                score=hit.score,
                metadata={k: v for k, v in hit.payload.items() if k != "text"},
            )
            for hit in results.points
        ]

    # ── Delete ────────────────────────────────────────────

    async def delete_by_file(self, project_id: uuid.UUID, file_id: uuid.UUID) -> None:
        self._client.delete(
            collection_name=self._collection,
            points_selector=Filter(
                must=[
                    FieldCondition(key="project_id", match=MatchValue(value=str(project_id))),
                    FieldCondition(key="file_id", match=MatchValue(value=str(file_id))),
                ]
            ),
        )
        logger.info("Deleted vectors for file %s in project %s", file_id, project_id)
