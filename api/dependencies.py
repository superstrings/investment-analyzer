"""
FastAPI dependency injection.
"""

from typing import Generator, Optional

from sqlalchemy.orm import Session

from db.database import SessionLocal, get_session
from db.models import User


def get_db() -> Generator[Session, None, None]:
    """Database session dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def resolve_user(db: Session, username: str) -> Optional[User]:
    """Resolve username to User object."""
    return db.query(User).filter_by(username=username).first()
