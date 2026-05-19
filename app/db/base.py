import uuid

from sqlalchemy import Column, DateTime, String, TypeDecorator, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    On PostgreSQL the column is a real `UUID` (matches the type the Alembic
    migration creates with `postgresql.UUID(as_uuid=True)`); on every other
    backend (notably SQLite for tests) it falls back to CHAR(36).

    Without the dialect dispatch the model would advertise VARCHAR(36) on PG
    while the underlying column is UUID — queries still work because PG
    coerces strings to UUID, but composite indexes and raw SQL hit the
    string/UUID mismatch. The TypeDecorator pattern keeps Python-side values
    as `uuid.UUID` and lets each backend store the native shape.
    """

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, uuid.UUID) else uuid.UUID(value)


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
