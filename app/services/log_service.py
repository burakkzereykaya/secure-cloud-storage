from sqlalchemy.orm import Session

from app.db.models.access_log import AccessLog


def log_event(
    db: Session,
    user_id: int,
    file_id: int,
    action: str,
    status: str,
    ip_address: str | None = None,
) -> AccessLog:
    log = AccessLog(
        user_id=user_id,
        file_id=file_id,
        action=action,
        status=status,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log