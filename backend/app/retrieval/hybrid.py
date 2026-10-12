import math
import re
from dataclasses import dataclass
from functools import lru_cache

from app.core.config import get_settings


@dataclass
class Retrieved:
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    text: str
    score: float = 0.0


def cosine(a: list[float], b: list[float]) -> float:
    if not a or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b)) / ((math.sqrt(sum(x*x for x in a)) or 1) * (math.sqrt(sum(y*y for y in b)) or 1))


def reciprocal_rank_fusion(rankings: list[list[Retrieved]], k: int = 60) -> list[Retrieved]:
    scores: dict[str, float] = {}
    items: dict[str, Retrieved] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, 1):
            scores[item.chunk_id] = scores.get(item.chunk_id, 0) + 1 / (k + rank)
            items[item.chunk_id] = item
    for chunk_id, score in scores.items():
        items[chunk_id].score = score
    return sorted(items.values(), key=lambda item: item.score, reverse=True)


def keyword_rank(query: str, items: list[Retrieved]) -> list[Retrieved]:
    corpus = [re.findall(r"\w+", item.text.lower()) for item in items]
    tokens = re.findall(r"\w+", query.lower())
    try:
        from rank_bm25 import BM25Okapi
        scores = BM25Okapi(corpus).get_scores(tokens)
    except Exception:
        wanted = set(tokens)
        scores = [sum(words.count(token) for token in wanted) / max(len(words), 1) for words in corpus]
    return [item for _, item in sorted(zip(scores, items), key=lambda pair: pair[0], reverse=True)]


def semantic_rank(query_vector: list[float], vectors: dict[str, list[float]], items: list[Retrieved]) -> list[Retrieved]:
    return sorted(items, key=lambda item: cosine(query_vector, vectors.get(item.chunk_id, [])), reverse=True)


@dataclass(frozen=True)
class RerankResult:
    items: list[Retrieved]
    backend: str


@lru_cache(maxsize=1)
def _cross_encoder():
    try:
        from sentence_transformers import CrossEncoder
        return CrossEncoder(get_settings().reranker_model, local_files_only=True)
    except Exception:
        return None


def rerank_with_metadata(query: str, items: list[Retrieved], limit: int) -> RerankResult:
    if not items:
        return RerankResult([], "none")
    model = _cross_encoder()
    if model is not None:
        scores = model.predict([(query, item.text) for item in items])
        ranked = [item for _, item in sorted(zip(scores, items), key=lambda pair: pair[0], reverse=True)]
        backend = "cross-encoder"
    else:
        # Deterministic lexical reranker used when model weights are not installed.
        tokens = set(re.findall(r"\w+", query.lower()))
        ranked = sorted(items, key=lambda item: len(tokens & set(re.findall(r"\w+", item.text.lower()))) / max(len(tokens), 1), reverse=True)
        backend = "lexical-fallback"
    return RerankResult(ranked[:limit], backend)


def rerank(query: str, items: list[Retrieved], limit: int) -> list[Retrieved]:
    return rerank_with_metadata(query, items, limit).items


def relevance_score(query: str, query_vector: list[float], vector: list[float], text: str) -> float:
    stop = {"what", "when", "where", "which", "that", "this", "with", "from", "have", "does", "about", "were", "into"}
    query_terms = {word for word in re.findall(r"[a-z0-9]+", query.lower()) if len(word) > 2 and word not in stop}
    passage_terms = set(re.findall(r"[a-z0-9]+", text.lower()))
    lexical = len(query_terms & passage_terms) / max(len(query_terms), 1)
    semantic = max(0.0, cosine(query_vector, vector)) if vector else 0.0
    return max(lexical, semantic)

