# Architecture

AI Document Search is a modular monolith: one React client, one FastAPI process, PostgreSQL for durable application state, and Qdrant for vector retrieval. This keeps authorization and transactional data in one security boundary.

## Request flow

1. JWT authentication resolves a database user.
2. Document IDs are authorized against PostgreSQL before retrieval.
3. PyMuPDF extracts text per page; the chunker retains page and position metadata.
4. Sentence Transformers generates vectors when local weights exist. A deterministic hashing embedder keeps development reproducible without downloads.
5. Chunks are persisted in PostgreSQL for provenance and Qdrant for vector search. Qdrant metadata is never treated as the authorization authority.
6. BM25 and semantic rankings are merged with reciprocal rank fusion and reranked by a cross-encoder. Missing local weights trigger a labelled lexical fallback.
7. Suspicious retrieved passages are excluded and a minimum evidence threshold can force an insufficient-evidence response. The current release builds extractive answers only; external provider settings are reserved and are not wired to generation.
8. Citation chunk/document/page tuples are validated against stored chunks. Each generated claim is checked only against the specific cited passage attached to it.

## Trust boundaries

PDF text is untrusted. Injection heuristics flag hostile passages for audit; they cannot change system behavior. Ownership checks, response validation, file restrictions, token expiry, rate limiting, output redaction, and minimal audit events are deterministic controls. Automated verification is evidence assistance—not proof—and the UI always exposes passages.

## Production scaling

Replace in-process background ingestion with a durable worker before horizontal scaling. Keep the same job table and idempotent chunk IDs. Put TLS and an identity-aware proxy in front of the frontend, use managed PostgreSQL/Qdrant backups, object storage with malware scanning, key rotation, centralized rate limiting, and structured telemetry without document text.

