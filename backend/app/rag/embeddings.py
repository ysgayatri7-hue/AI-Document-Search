import hashlib
import math
import re
from functools import lru_cache

from app.core.config import get_settings


def hashing_embedding(text: str, dimensions: int = 256) -> list[float]:
    vector = [0.0] * dimensions
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += 1.0 if digest[4] & 1 else -1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


@lru_cache(maxsize=1)
def _model():
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(get_settings().embedding_model, local_files_only=True)
    except Exception:
        return None


def embed_texts(texts: list[str]) -> list[list[float]]:
    model = _model()
    if model is None:
        return [hashing_embedding(text) for text in texts]
    return model.encode(texts, normalize_embeddings=True).tolist()


def embedding_backend() -> str:
    """Expose the real active backend; never imply a model ran when it did not."""
    return "sentence-transformer" if _model() is not None else "hashing-fallback"

