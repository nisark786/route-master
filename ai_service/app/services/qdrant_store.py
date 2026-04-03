from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.services.embedding import embedding_service


def _distance_from_setting() -> qmodels.Distance:
    mapping = {
        "cosine": qmodels.Distance.COSINE,
        "dot": qmodels.Distance.DOT,
        "euclid": qmodels.Distance.EUCLID,
        "manhattan": qmodels.Distance.MANHATTAN,
    }
    return mapping.get(settings.qdrant_distance, qmodels.Distance.COSINE)


class QdrantStore:
    def __init__(self) -> None:
        self.client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=20,
        )
        self.collection = settings.qdrant_collection

    def ensure_collection(self) -> None:
        collections = self.client.get_collections().collections
        exists = any(col.name == self.collection for col in collections)
        if not exists:
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=qmodels.VectorParams(
                    size=settings.embedding_dim,
                    distance=_distance_from_setting(),
                ),
            )

        # Always ensure required payload indexes exist, even for pre-existing collections.
        self.client.create_payload_index(
            collection_name=self.collection,
            field_name="tenant_id",
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
        )
        self.client.create_payload_index(
            collection_name=self.collection,
            field_name="doc_id",
            field_schema=qmodels.PayloadSchemaType.KEYWORD,
        )

    def upsert_chunks(
        self,
        tenant_id: str,
        doc_id: str,
        chunks: list[str],
        metadata: dict,
    ) -> int:
        vectors = embedding_service.embed_texts(chunks)
        points: list[qmodels.PointStruct] = []

        for index, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}:{index}"
            payload = {
                "tenant_id": tenant_id,
                "doc_id": doc_id,
                "chunk_id": chunk_id,
                "text": chunk,
                "metadata": metadata or {},
            }
            points.append(
                qmodels.PointStruct(
                    id=str(uuid4()),
                    vector=vectors[index],
                    payload=payload,
                )
            )

        self.client.upsert(collection_name=self.collection, points=points, wait=True)
        return len(points)

    def search(self, tenant_id: str, query: str, top_k: int) -> list[qmodels.ScoredPoint]:
        vector = embedding_service.embed_query(query)
        tenant_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="tenant_id",
                    match=qmodels.MatchValue(value=tenant_id),
                )
            ]
        )
        return self.client.search(
            collection_name=self.collection,
            query_vector=vector,
            query_filter=tenant_filter,
            limit=top_k,
            with_payload=True,
            with_vectors=False,
        )

    def delete_document(self, tenant_id: str, doc_id: str) -> int:
        doc_filter = qmodels.Filter(
            must=[
                qmodels.FieldCondition(
                    key="tenant_id",
                    match=qmodels.MatchValue(value=tenant_id),
                ),
                qmodels.FieldCondition(
                    key="doc_id",
                    match=qmodels.MatchValue(value=doc_id),
                ),
            ]
        )

        deleted = 0
        next_offset = None
        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection,
                scroll_filter=doc_filter,
                with_payload=False,
                with_vectors=False,
                limit=200,
                offset=next_offset,
            )
            if not points:
                break
            ids = [point.id for point in points]
            self.client.delete(
                collection_name=self.collection,
                points_selector=qmodels.PointIdsList(points=ids),
                wait=True,
            )
            deleted += len(ids)
            if next_offset is None:
                break
        return deleted


qdrant_store = QdrantStore()
