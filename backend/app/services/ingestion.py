from pathlib import Path

import fitz
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.guardrails.safety import document_is_suspicious
from app.models.entities import Chunk, Document, DocumentProcessingJob, DocumentStatus
from app.rag.chunking import chunk_pages
from app.rag.embeddings import embed_texts, embedding_backend
from app.retrieval.vector_store import upsert_chunks
from app.services.audit import audit


def extract_pdf(path: Path) -> list[tuple[int, str]]:
    settings = get_settings()
    try:
        with fitz.open(path) as pdf:
            if not pdf.is_pdf:
                raise ValueError("The uploaded file is not a PDF")
            if pdf.needs_pass:
                raise ValueError("Password-protected PDFs are not supported")
            if pdf.page_count > settings.max_pdf_pages:
                raise ValueError(f"PDF exceeds the {settings.max_pdf_pages}-page processing limit")
            if hasattr(pdf, "embfile_count") and pdf.embfile_count() > 0:
                raise ValueError("PDFs containing embedded files are not accepted")
            pages: list[tuple[int, str]] = []
            extracted_chars = 0
            for number, page in enumerate(pdf):
                text = page.get_text("text")
                extracted_chars += len(text)
                if extracted_chars > settings.max_pdf_text_chars:
                    raise ValueError("Extracted PDF text exceeds the safe processing limit")
                pages.append((number + 1, text))
            return pages
    except fitz.FileDataError as exc:
        raise ValueError("The uploaded file is not a readable PDF") from exc


def process_document(db: Session, document_id: str) -> None:
    settings = get_settings()
    document = db.get(Document, document_id)
    if not document:
        return
    job = db.scalar(select(DocumentProcessingJob).where(
        DocumentProcessingJob.document_id == document_id
    ).order_by(DocumentProcessingJob.created_at.desc()))
    if not job:
        return
    try:
        job.status, job.progress = "extracting", 15
        db.commit()
        pages = extract_pdf(Path(document.storage_path))
        document.page_count = len(pages)
        if not pages or sum(len(text.strip()) for _, text in pages) < 40:
            raise ValueError("No usable text was found. The PDF may be scanned; OCR is not enabled.")
        chunks = chunk_pages(pages, settings.chunk_size, settings.chunk_overlap)
        if not chunks:
            raise ValueError("The PDF did not produce any indexable passages")
        job.status, job.progress = "embedding", 55
        db.commit()
        vectors = embed_texts([item.text for item in chunks])
        db.execute(delete(Chunk).where(Chunk.document_id == document.id))
        suspicious = 0
        for item, vector in zip(chunks, vectors):
            chunk_id = f"{document.id}:{item.page_number}:{item.position}"
            suspicious += int(document_is_suspicious(item.text))
            db.add(Chunk(id=chunk_id, document_id=document.id, owner_id=document.owner_id,
                         page_number=item.page_number, position=item.position, text=item.text, embedding=vector))
        indexed_in_qdrant = upsert_chunks([
            {"point_id": index + 1 + int(document.sha256[:8], 16) * 100000,
             "vector": vector, "chunk_id": f"{document.id}:{item.page_number}:{item.position}",
             "document_id": document.id, "owner_id": document.owner_id,
             "page_number": item.page_number, "text": item.text}
            for index, (item, vector) in enumerate(zip(chunks, vectors))
        ], len(vectors[0]))
        if settings.qdrant_url and not indexed_in_qdrant:
            raise RuntimeError("Vector indexing failed; the document was not marked indexed")
        document.status, document.error_message = DocumentStatus.indexed, None
        job.status, job.progress = "completed", 100
        audit(db, "document.indexed", document.owner_id, "document", document.id, {
            "pages": len(pages), "chunks": len(chunks), "suspicious_passages": suspicious,
            "embedding_backend": embedding_backend(),
            "vector_store": "qdrant" if indexed_in_qdrant else "local",
        })
        db.commit()
    except Exception as exc:
        document.status, document.error_message = DocumentStatus.failed, str(exc)[:500]
        job.status, job.error_message = "failed", str(exc)[:500]
        audit(db, "document.processing_failed", document.owner_id, "document", document.id,
              {"error_type": type(exc).__name__})
        db.commit()


def process_document_task(document_id: str) -> None:
    """Background-task boundary with an independent database session."""
    with SessionLocal() as db:
        process_document(db, document_id)
