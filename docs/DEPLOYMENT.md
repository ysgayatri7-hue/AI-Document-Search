# Production deployment checklist

- Set a random `SECRET_KEY` of at least 32 bytes and a strong `POSTGRES_PASSWORD`.
- Set exact HTTPS `CORS_ORIGINS`; never use `*` with credentials.
- Terminate TLS at a trusted reverse proxy and enforce HSTS there.
- Store secrets in the platform secret manager, not `.env` in source control.
- Back up PostgreSQL, Qdrant, and the upload volume together; test restoration.
- Restrict Qdrant and PostgreSQL to the private network.
- Add malware scanning and encrypted object storage before accepting public uploads.
- Configure an external rate-limit store before horizontal API scaling.
- Pre-download and pin approved embedding/reranking model weights.
- Run migrations as a release step, then deploy the API and frontend.
- Review audit retention, privacy requirements, and deletion procedures.
- Run the adversarial tests and a human-labelled evaluation set before release.

Start: `docker compose up --build -d`. Inspect: `docker compose ps` and `docker compose logs -f backend`. Stop without deleting data: `docker compose down`. Destructive removal of volumes: `docker compose down -v`.

