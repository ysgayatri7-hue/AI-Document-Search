import hashlib
import os
import re
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import Base, engine, get_db
from app.models.entities import (Answer, AuditLog, Chunk, Citation, Claim, Document,
                                 DocumentProcessingJob, DocumentStatus, EvaluationRun,
                                 Feedback, Query, User)
from app.schemas.api import FeedbackRequest, LoginRequest, QueryRequest, RegisterRequest, TokenView, UserView
from app.security.auth import create_token, get_current_user, hash_password, verify_password
from app.services.answering import answer_question
from app.services.audit import audit
from app.services.ingestion import process_document_task
from app.retrieval.vector_store import delete_document as delete_vectors

settings = get_settings()

@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.environment == "production" and (len(settings.secret_key) < 32 or settings.secret_key.startswith("development")):
        raise RuntimeError("A strong SECRET_KEY is required in production")
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(engine)
    yield

app = FastAPI(title="AI Document Search API", version="1.0.0", description="Grounded document search and claim verification", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
                   allow_methods=["GET", "POST", "DELETE"], allow_headers=["Authorization", "Content-Type"])
requests_by_ip: dict[str, deque[float]] = defaultdict(deque)
dummy_password_hash = hash_password("dummy-password-used-only-for-timing")


def security_headers(request_id: str) -> dict[str, str]:
    return {
        "X-Request-ID": request_id,
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "no-referrer",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        "Cache-Control": "no-store",
    }

@app.middleware("http")
async def security_and_rate_limit(request: Request, call_next):
    request_id = os.urandom(8).hex()
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    bucket = requests_by_ip[client]
    while bucket and bucket[0] < now - 60:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_per_minute and request.url.path != "/api/health":
        return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429, headers=security_headers(request_id))
    bucket.append(now)
    response = await call_next(request)
    response.headers.update(security_headers(request_id))
    return response


def user_view(user: User) -> dict:
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "created_at": user.created_at}


def document_view(db: Session, doc: Document) -> dict:
    progress = db.scalar(select(DocumentProcessingJob.progress).where(DocumentProcessingJob.document_id == doc.id)
                         .order_by(DocumentProcessingJob.created_at.desc()).limit(1)) or 0
    return {"id": doc.id, "filename": doc.filename, "size_bytes": doc.size_bytes,
            "page_count": doc.page_count, "status": doc.status.value, "error_message": doc.error_message,
            "progress": progress, "created_at": doc.created_at}


def answer_view(db: Session, query: Query) -> dict:
    answer = db.scalar(select(Answer).where(Answer.query_id == query.id))
    if not answer:
        return {"id": query.id, "question": query.question, "status": query.status, "answer": None}
    citations = list(db.scalars(select(Citation).where(Citation.answer_id == answer.id).order_by(Citation.rank)))
    documents = {d.id: d for d in db.scalars(select(Document).where(Document.id.in_([c.document_id for c in citations])))} if citations else {}
    claims = list(db.scalars(select(Claim).where(Claim.answer_id == answer.id)))
    return {"id": query.id, "question": query.question, "status": query.status, "created_at": query.created_at,
            "retrieval_latency_ms": round(query.retrieval_latency_ms, 2), "total_latency_ms": round(query.total_latency_ms, 2),
            "answer": {"id": answer.id, "text": answer.text, "mode": answer.mode,
                       "insufficient_evidence": answer.insufficient_evidence, "limitations": answer.limitations,
                       "citations": [{"id": c.id, "number": c.rank, "document_id": c.document_id,
                                      "filename": documents[c.document_id].filename if c.document_id in documents else "Deleted document",
                                      "page_number": c.page_number, "excerpt": c.excerpt, "valid": c.valid} for c in citations],
                       "claims": [{"id": c.id, "text": c.text, "status": c.status.value,
                                   "evidence_citation_ids": c.evidence_citation_ids, "rationale": c.rationale} for c in claims]}}


@app.get("/api/health", tags=["system"])
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "reachable", "llm_provider": settings.llm_provider,
            "generation_available": settings.llm_provider == "extractive"}


@app.post("/api/auth/register", response_model=TokenView, tags=["auth"], status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = User(email=payload.email.lower(), display_name=payload.display_name.strip(), password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "An account with this email already exists") from exc
    audit(db, "auth.registered", user.id)
    db.commit()
    return {"access_token": create_token(user.id), "user": user_view(user)}


@app.post("/api/auth/login", response_model=TokenView, tags=["auth"])
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    password_valid = verify_password(payload.password, user.password_hash if user else dummy_password_hash)
    if not user or not password_valid:
        audit(db, "auth.login_failed", None, metadata={"reason": "invalid_credentials"})
        db.commit()
        raise HTTPException(401, "Invalid email or password")
    audit(db, "auth.login", user.id)
    db.commit()
    return {"access_token": create_token(user.id), "user": user_view(user)}


@app.get("/api/auth/me", response_model=UserView, tags=["auth"])
def me(user: User = Depends(get_current_user)):
    return user_view(user)


@app.post("/api/documents", status_code=201, tags=["documents"])
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    filename = re.sub(r"[\x00-\x1f\x7f]", "", Path(file.filename or "document.pdf").name).strip() or "document.pdf"
    if file.content_type not in {"application/pdf", "application/octet-stream"} or not filename.lower().endswith(".pdf"):
        raise HTTPException(415, "Only PDF files are accepted")
    content = await file.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(413, f"PDF exceeds the {settings.max_upload_mb} MB limit")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(415, "The uploaded content is not a valid PDF")
    digest = hashlib.sha256(content).hexdigest()
    existing = db.scalar(select(Document).where(Document.owner_id == user.id, Document.sha256 == digest))
    if existing:
        raise HTTPException(409, "This document has already been uploaded")
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename)[:180]
    target_dir = settings.upload_dir / user.id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{digest[:16]}-{safe_name}"
    target.write_bytes(content)
    doc = Document(owner_id=user.id, filename=filename[:255], storage_path=str(target), size_bytes=len(content), sha256=digest)
    db.add(doc); db.flush()
    db.add(DocumentProcessingJob(document_id=doc.id, status="queued", progress=0))
    audit(db, "document.uploaded", user.id, "document", doc.id, {"size_bytes": len(content)})
    db.commit()
    background_tasks.add_task(process_document_task, doc.id)
    return document_view(db, doc)


@app.get("/api/documents", tags=["documents"])
def list_documents(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = db.scalars(select(Document).where(Document.owner_id == user.id).order_by(Document.created_at.desc()))
    return [document_view(db, doc) for doc in docs]


@app.get("/api/documents/{document_id}", tags=["documents"])
def get_document(document_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.scalar(select(Document).where(Document.id == document_id, Document.owner_id == user.id))
    if not doc: raise HTTPException(404, "Document not found")
    return document_view(db, doc)


@app.get("/api/documents/{document_id}/content", tags=["documents"])
def preview_document(document_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.scalar(select(Document).where(Document.id == document_id, Document.owner_id == user.id))
    if not doc or not Path(doc.storage_path).is_file():
        raise HTTPException(404, "Document not found")
    return FileResponse(doc.storage_path, media_type="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{Path(doc.filename).name}"'})


@app.delete("/api/documents/{document_id}", status_code=204, tags=["documents"])
def delete_document(document_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.scalar(select(Document).where(Document.id == document_id, Document.owner_id == user.id))
    if not doc: raise HTTPException(404, "Document not found")
    path = Path(doc.storage_path)
    delete_vectors(doc.id)
    audit(db, "document.deleted", user.id, "document", doc.id)
    db.delete(doc); db.commit()
    path.unlink(missing_ok=True)


@app.post("/api/documents/{document_id}/retry", tags=["documents"])
def retry_document(document_id: str, background_tasks: BackgroundTasks, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    doc = db.scalar(select(Document).where(Document.id == document_id, Document.owner_id == user.id))
    if not doc: raise HTTPException(404, "Document not found")
    doc.status, doc.error_message = DocumentStatus.processing, None
    attempts = db.scalar(select(func.count()).select_from(DocumentProcessingJob).where(DocumentProcessingJob.document_id == doc.id)) or 0
    db.add(DocumentProcessingJob(document_id=doc.id, attempt=attempts + 1)); db.commit()
    background_tasks.add_task(process_document_task, doc.id)
    return document_view(db, doc)


@app.post("/api/query", status_code=201, tags=["questions"])
def query(payload: QueryRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        row = answer_question(db, user.id, payload.question, payload.document_ids)
    except HTTPException as exc:
        if exc.status_code == 400:
            audit(db, "security.prompt_injection_blocked", user.id, metadata={"source": "user_input"})
            db.commit()
        raise
    return answer_view(db, row)


@app.get("/api/query/{query_id}", tags=["questions"])
def get_query(query_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(Query).where(Query.id == query_id, Query.user_id == user.id))
    if not row: raise HTTPException(404, "Question not found")
    return answer_view(db, row)


@app.get("/api/history", tags=["questions"])
def history(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Query).where(Query.user_id == user.id).order_by(Query.created_at.desc()).limit(100))
    return [answer_view(db, row) for row in rows]


@app.post("/api/feedback", status_code=201, tags=["questions"])
def feedback(payload: FeedbackRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    answer = db.scalar(select(Answer).join(Query).where(Answer.id == payload.answer_id, Query.user_id == user.id))
    if not answer: raise HTTPException(404, "Answer not found")
    existing = db.scalar(select(Feedback).where(Feedback.answer_id == answer.id, Feedback.user_id == user.id))
    if existing:
        existing.helpful, existing.comment = payload.helpful, payload.comment
    else:
        db.add(Feedback(user_id=user.id, answer_id=answer.id, helpful=payload.helpful, comment=payload.comment))
    audit(db, "answer.feedback", user.id, "answer", answer.id, {"helpful": payload.helpful}); db.commit()
    return {"status": "recorded"}


@app.get("/api/analytics/overview", tags=["analytics"])
def analytics_overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = db.scalar(select(func.count()).select_from(Document).where(Document.owner_id == user.id)) or 0
    indexed = db.scalar(select(func.count()).select_from(Document).where(Document.owner_id == user.id, Document.status == DocumentStatus.indexed)) or 0
    query_count = db.scalar(select(func.count()).select_from(Query).where(Query.user_id == user.id)) or 0
    latencies = list(db.scalars(select(Query.total_latency_ms).where(Query.user_id == user.id)))
    supported = db.scalar(select(func.count()).select_from(Claim).join(Answer).join(Query).where(Query.user_id == user.id, Claim.status == "supported")) or 0
    claim_count = db.scalar(select(func.count()).select_from(Claim).join(Answer).join(Query).where(Query.user_id == user.id)) or 0
    return {"documents": docs, "indexed_documents": indexed, "questions": query_count,
            "claims_verified": claim_count, "supported_claims": supported,
            "median_latency_ms": sorted(latencies)[len(latencies)//2] if latencies else None,
            "evaluation": None}


@app.get("/api/analytics/verification", tags=["analytics"])
def analytics_verification(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.execute(select(Claim.status, func.count()).join(Answer).join(Query).where(Query.user_id == user.id).group_by(Claim.status)).all()
    latest_eval = db.scalar(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(1))
    return {"live": {status.value: count for status, count in rows},
            "offline_evaluation": latest_eval.metrics if latest_eval else None}

