from sqlalchemy.orm import Session

from app.models.entities import AuditLog


def audit(db: Session, event_type: str, user_id: str | None = None, resource_type: str | None = None,
          resource_id: str | None = None, metadata: dict | None = None) -> None:
    # Never store questions, answers, passwords, tokens, or document text here.
    db.add(AuditLog(user_id=user_id, event_type=event_type, resource_type=resource_type,
                    resource_id=resource_id, metadata_json=metadata or {}))

