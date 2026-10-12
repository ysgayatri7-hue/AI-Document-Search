# Security policy

Please report vulnerabilities privately to the repository owner. Do not open a public issue containing secrets, personal data, or exploit details.

The current release validates PDF signatures, size, page count, extracted-text volume, encryption state, and embedded-file presence. It hashes passwords with Argon2, expires JWTs, scopes document/chunk/query access to the authenticated owner, parameterizes database access through SQLAlchemy, rate-limits requests, applies CORS and defensive response headers, records content-free audit metadata, rejects common instruction-override phrases, validates citation provenance, and redacts SSN- and payment-number-shaped output.

These controls do not make arbitrary PDFs or model inputs safe. Residual risks include parser vulnerabilities, image-only or steganographic content, prompt-injection variants that bypass heuristics, sensitive data outside the narrow redaction patterns, stolen browser-local-storage tokens after XSS, interrupted in-process indexing jobs, denial of service across multiple application replicas, and errors from automated claim verification. There is no antivirus/content-disarm pipeline, OCR sandbox, enterprise SSO, distributed rate limiter, durable worker, or external LLM adapter. Use a malware scanning/CDR service, isolated extraction workers with resource limits, an HttpOnly-cookie/BFF authentication design, shared rate limiting, durable queues, dependency scanning, and human review before internet or high-sensitivity deployment. Review `docs/DEPLOYMENT.md` before exposure.

