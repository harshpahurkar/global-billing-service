from sqlalchemy import Boolean, Column, DateTime, String

from app.db.base import Base, TimestampMixin, UUIDMixin


class APIKey(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "api_keys"

    name = Column(String(255), nullable=False)
    hashed_key = Column(String(64), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<APIKey(id={self.id}, name={self.name}, active={self.is_active})>"
