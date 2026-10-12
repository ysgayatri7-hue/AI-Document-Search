from functools import lru_cache

from app.core.config import get_settings


@lru_cache(maxsize=1)
def client():
    settings = get_settings()
    if not settings.qdrant_url:
        return None
    try:
        from qdrant_client import QdrantClient
        return QdrantClient(url=settings.qdrant_url, timeout=10)
    except Exception:
        return None


def collection_name(vector_size: int) -> str:
    """Version collections by vector size so model changes cannot corrupt indexing."""
    return f"{get_settings().qdrant_collection}_d{vector_size}"


def upsert_chunks(items: list[dict], vector_size: int) -> bool:
    qdrant = client()
    if qdrant is None:
        return False
    name = collection_name(vector_size)
    try:
        from qdrant_client.models import Distance, PointStruct, VectorParams
        if not qdrant.collection_exists(name):
            qdrant.create_collection(
                name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        points = [
            PointStruct(
                id=item["point_id"],
                vector=item["vector"],
                payload={key: value for key, value in item.items() if key not in {"point_id", "vector"}},
            )
            for item in items
        ]
        qdrant.upsert(name, points=points, wait=True)
        return True
    except Exception:
        return False


def delete_document(document_id: str) -> None:
    qdrant = client()
    if qdrant is None:
        return
    try:
        from qdrant_client.models import FieldCondition, Filter, MatchValue
        base = get_settings().qdrant_collection
        collections = qdrant.get_collections().collections
        names = [item.name for item in collections if item.name == base or item.name.startswith(f"{base}_d")]
        selector = Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))])
        for name in names:
            qdrant.delete(name, points_selector=selector, wait=True)
    except Exception:
        pass


def search_chunks(vector: list[float], owner_id: str, document_ids: list[str], limit: int) -> list[str]:
    """Return chunk IDs from Qdrant after deterministic PostgreSQL authorization."""
    qdrant = client()
    if qdrant is None or not document_ids or not vector:
        return []
    try:
        from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue
        query_filter = Filter(must=[
            FieldCondition(key="owner_id", match=MatchValue(value=owner_id)),
            FieldCondition(key="document_id", match=MatchAny(any=document_ids)),
        ])
        result = qdrant.query_points(
            collection_name=collection_name(len(vector)),
            query=vector,
            query_filter=query_filter,
            limit=limit,
            with_payload=True,
        )
        return [str(point.payload["chunk_id"]) for point in result.points]
    except Exception:
        return []

