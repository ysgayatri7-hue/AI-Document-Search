import re
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.guardrails.safety import document_is_suspicious, sanitize_output, validate_question
from app.models.entities import Answer, Chunk, Citation, Claim, Document, DocumentStatus, Query
from app.rag.embeddings import embed_texts, embedding_backend
from app.retrieval.hybrid import (
    Retrieved, keyword_rank, reciprocal_rank_fusion, relevance_score,
    rerank_with_metadata, semantic_rank,
)
from app.retrieval.vector_store import search_chunks
from app.services.audit import audit
from app.verification.verifier import validate_citation, verify_claim


def _best_supported_sentence(passage: str, question: str) -> str:
    """Choose a complete evidence sentence instead of slicing arbitrary characters."""
    sentences = [item.strip() for item in re.split(r"(?<=[.!?])\s+|\n+", passage) if len(item.strip()) >= 20]
    if not sentences:
        return passage.strip()[:360]
    terms = {word for word in re.findall(r"[a-z0-9]+", question.lower()) if len(word) > 2}
    best = max(sentences, key=lambda sentence: len(terms & set(re.findall(r"[a-z0-9]+", sentence.lower()))))
    return best if len(best) <= 420 else best[:417].rsplit(" ", 1)[0] + "…"


def answer_question(db: Session, user_id: str, question: str, document_ids: list[str]) -> Query:
    settings = get_settings()
    started = time.perf_counter()
    question = validate_question(question)
    if document_ids:
        owned = list(db.scalars(select(Document).where(
            Document.owner_id == user_id, Document.id.in_(document_ids)
        )))
        if set(document_ids) != {document.id for document in owned}:
            from fastapi import HTTPException
            raise HTTPException(403, "One or more documents are not available to your account")
        if any(document.status != DocumentStatus.indexed for document in owned):
            from fastapi import HTTPException
            raise HTTPException(409, "One or more selected documents have not finished indexing")
        documents = owned
    else:
        documents = list(db.scalars(select(Document).where(
            Document.owner_id == user_id, Document.status == DocumentStatus.indexed
        )))
    allowed = {doc.id: doc for doc in documents}

    query_row = Query(user_id=user_id, question=question, document_ids=list(allowed))
    db.add(query_row)
    db.flush()
    chunks = list(db.scalars(select(Chunk).where(
        Chunk.owner_id == user_id, Chunk.document_id.in_(list(allowed))
    ))) if allowed else []
    safe_chunks = [chunk for chunk in chunks if not document_is_suspicious(chunk.text)]
    blocked_passages = len(chunks) - len(safe_chunks)
    retrieved = [Retrieved(chunk.id, chunk.document_id, allowed[chunk.document_id].filename,
                           chunk.page_number, chunk.text) for chunk in safe_chunks]

    retrieval_started = time.perf_counter()
    passages: list[Retrieved] = []
    reranker_backend = "none"
    semantic_backend = "none"
    active_embedding_backend = "none"
    vectors = {chunk.id: chunk.embedding or [] for chunk in safe_chunks}
    if retrieved:
        query_vector = embed_texts([question])[0]
        active_embedding_backend = embedding_backend()
        qdrant_ids = search_chunks(query_vector, user_id, list(allowed), 24)
        by_id = {item.chunk_id: item for item in retrieved}
        semantic = [by_id[chunk_id] for chunk_id in qdrant_ids if chunk_id in by_id]
        if semantic:
            semantic_backend = "qdrant"
        else:
            semantic = semantic_rank(query_vector, vectors, retrieved)
            semantic_backend = "local-vector-fallback"
        fused = reciprocal_rank_fusion([keyword_rank(question, retrieved), semantic])
        reranked = rerank_with_metadata(question, fused[:24], settings.retrieval_top_k)
        reranker_backend = reranked.backend
        passages = [item for item in reranked.items if relevance_score(
            question, query_vector, vectors.get(item.chunk_id, []), item.text
        ) >= settings.minimum_relevance_score]
    query_row.retrieval_latency_ms = (time.perf_counter() - retrieval_started) * 1000

    limitations: list[str] = []
    if active_embedding_backend == "hashing-fallback":
        limitations.append("Sentence Transformer weights were unavailable; deterministic hashing embeddings were used.")
    if reranker_backend == "lexical-fallback":
        limitations.append("Cross-encoder weights were unavailable; deterministic lexical reranking was used.")
    if semantic_backend == "local-vector-fallback" and settings.qdrant_url:
        limitations.append("Qdrant returned no authorized candidates; local vector ranking was used.")
    if blocked_passages:
        limitations.append(f"{blocked_passages} passage(s) containing instruction-override language were excluded.")

    if not passages:
        db.add(Answer(
            query_id=query_row.id,
            text="I could not find sufficient evidence in your indexed documents to answer this question.",
            insufficient_evidence=True,
            limitations=limitations + ["No passage met the configured evidence relevance threshold."],
            mode="extractive",
        ))
    else:
        selected = passages[:3]
        claims = [_best_supported_sentence(passage.text, question) for passage in selected]
        answer_text = sanitize_output(" ".join(f"{claim} [{index}]" for index, claim in enumerate(claims, 1)))
        answer = Answer(
            query_id=query_row.id,
            text=answer_text,
            mode="extractive",
            limitations=limitations + ["Extractive mode quotes evidence; automated verification can make mistakes."],
        )
        db.add(answer)
        db.flush()
        available = {chunk.id: (chunk.page_number, chunk.document_id) for chunk in safe_chunks}
        citations: list[Citation] = []
        for index, passage in enumerate(selected, 1):
            citation = Citation(
                answer_id=answer.id, chunk_id=passage.chunk_id, document_id=passage.document_id,
                page_number=passage.page_number, excerpt=sanitize_output(passage.text[:700]), rank=index,
                valid=validate_citation(passage.chunk_id, passage.page_number, available, passage.document_id),
            )
            db.add(citation)
            db.flush()
            citations.append(citation)
        for claim_text, citation, passage in zip(claims, citations, selected):
            verification = verify_claim(claim_text, [passage.text])
            db.add(Claim(
                answer_id=answer.id, text=sanitize_output(claim_text), status=verification.status,
                evidence_citation_ids=[citation.id] if verification.evidence_indexes else [],
                rationale=verification.rationale,
            ))

    query_row.total_latency_ms = (time.perf_counter() - started) * 1000
    audit(db, "query.completed", user_id, "query", query_row.id, {
        "document_count": len(allowed), "retrieved_count": len(passages),
        "blocked_passages": blocked_passages, "embedding_backend": active_embedding_backend,
        "semantic_backend": semantic_backend, "reranker_backend": reranker_backend,
        "generation_mode": "extractive",
    })
    db.commit()
    return query_row
