import sys
from types import SimpleNamespace

from app.retrieval.hybrid import cosine
from app.retrieval import vector_store
from app.retrieval.vector_store import collection_name


def test_collection_name_is_versioned_by_embedding_dimension():
    assert collection_name(384).endswith("_d384")
    assert collection_name(256).endswith("_d256")
    assert collection_name(384) != collection_name(256)


def test_cosine_rejects_mixed_embedding_dimensions():
    assert cosine([1.0, 0.0], [1.0]) == 0.0
    assert cosine([], []) == 0.0
    assert cosine([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_upsert_uses_dimension_versioned_collection(monkeypatch):
    class VectorParams:
        def __init__(self, size, distance):
            self.size = size
            self.distance = distance

    class PointStruct:
        def __init__(self, **values):
            self.__dict__.update(values)

    models = SimpleNamespace(
        Distance=SimpleNamespace(COSINE="cosine"),
        PointStruct=PointStruct,
        VectorParams=VectorParams,
    )
    monkeypatch.setitem(sys.modules, "qdrant_client.models", models)

    class FakeQdrant:
        def __init__(self):
            self.created = None
            self.upserted = None

        def collection_exists(self, name):
            return False

        def create_collection(self, name, vectors_config):
            self.created = (name, vectors_config.size)

        def upsert(self, name, points, wait):
            self.upserted = (name, points, wait)

    fake = FakeQdrant()
    monkeypatch.setattr(vector_store, "client", lambda: fake)
    item = {
        "point_id": 1,
        "vector": [0.1, 0.2, 0.3],
        "chunk_id": "doc:1:0",
        "document_id": "doc",
        "owner_id": "owner",
        "page_number": 1,
        "text": "Evidence",
    }

    assert vector_store.upsert_chunks([item], 3) is True
    assert fake.created == (collection_name(3), 3)
    assert fake.upserted[0] == collection_name(3)
    assert fake.upserted[2] is True
