from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, DateTime, inspect
from sqlalchemy.orm import DeclarativeBase, declared_attr

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    id: Any

    # Generate __tablename__ automatically
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + "s"

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> dict:
        """Convert model instance to dictionary."""
        return {c.key: getattr(self, c.key) for c in inspect(self).mapper.column_attrs}
