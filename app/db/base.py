from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, DateTime, func
import uuid
from sqlalchemy.dialects.postgresql import UUID


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
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
