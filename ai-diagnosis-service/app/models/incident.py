import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    fingerprint: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    alert_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    namespace: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    pod: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    severity: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="open",
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index(
            "ix_incidents_fingerprint_status",
            "fingerprint",
            "status",
        ),
        Index(
            "uq_incident_active_fingerprint",
            "fingerprint",
            unique=True,
            postgresql_where=text(
                "status IN ('open', 'acknowledged')"
            ),
        ),
    )