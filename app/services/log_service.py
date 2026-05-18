from sqlalchemy.orm import Session

from app.db.models.access_log import AccessLog


def create_log(
    db: Session,
    user_id: int | None = None,
    file_id: int | None = None,
    action: str = "UNKNOWN",
    status: str = "UNKNOWN",
    ip_address: str | None = None,
    details: str | None = None,
) -> AccessLog:
    log = AccessLog(
        user_id=user_id,
        file_id=file_id,
        action=action,
        status=status,
        ip_address=ip_address,
        details=details,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log