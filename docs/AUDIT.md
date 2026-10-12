# Engineering audit

This document separates verified behavior from design intent. It is not a security certification.

## Verified in the automated suite

- PDF page numbers survive extraction and chunking and appear in validated response citations.
- Keyword (BM25) and vector rankings are fused with reciprocal-rank fusion; the selected reranker reports whether a real local cross-encoder or the labelled lexical fallback ran.
- Claims reference citation records and are evaluated against their own cited passage, not the entire retrieved context.
- Irrelevant evidence produces an insufficient-evidence response rather than a fabricated confidence score.
- Cross-account document metadata, deletion, querying, and PDF preview access are denied.
- Invalid signatures, embedded PDF files, prompt-override phrases, expired tokens, common passwords, and request-rate excesses are rejected.
- Qdrant failure does not mark a document indexed when Qdrant is configured.
- SSN- and payment-number-shaped values are redacted from answer text and citation excerpts.
- Failed authentication and blocked prompt attacks create audit events without storing the submitted secret or prompt.

## Honest fallbacks

Sentence Transformer and cross-encoder model weights are loaded locally only. When they are absent, deterministic hashing embeddings and lexical reranking keep development functional. Audit metadata and answer limitations identify those fallbacks. They are not equivalent to their model-backed counterparts.

## Residual risk

- PyMuPDF is still a complex parser. Page/size/attachment limits do not replace malware scanning, content disarm, process isolation, or OS-level resource limits.
- Injection matching covers common explicit phrases, not all semantic or obfuscated attacks. Retrieved text remains untrusted and is excluded when detected, but no classifier proves safety.
- Redaction covers only narrow numeric patterns and can miss names, addresses, account identifiers, secrets, and reformatted sensitive values.
- The limiter is per-process and IP based. It can be inconsistent behind proxies or across replicas until replaced with a trusted-proxy policy and shared store.
- Background tasks run inside the API process and are not durable across restarts.
- JWTs are stored in local storage. Same-origin script compromise can expose them.
- Automated entailment is lexical and can misclassify nuance, negation, tables, and cross-page claims. The UI exposes evidence for human review.
- No external generative provider is implemented in this release. `LLM_*` variables are reserved and an API key is not required for tested functionality.
- Default model identifiers are public repository names rather than immutable artifact digests. Pin reviewed revisions or mirror signed model artifacts for a controlled production supply chain.

## Release gates not performed by unit tests

Run dependency/SBOM scanning, container image scanning, a human-labelled retrieval and entailment evaluation, parser fuzzing, load testing, backup/restore testing, and an independent penetration test before processing sensitive production data.
