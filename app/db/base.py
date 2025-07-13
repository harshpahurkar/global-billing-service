from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime, String, func, TypeDecorator
import uuid


class GUID(TypeDecorator):
    """Platform-independent GUID type. Uses PostgreSQL UUID or CHAR(36)."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, uuid.UUID):
                return str(value)
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
        return value


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Mixin that adds created_at and updated_at timestamps."""
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDMixin:
    """Mixin that adds a UUID primary key."""
    id = Column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
