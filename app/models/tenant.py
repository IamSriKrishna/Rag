from sqlalchemy import Integer, String
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app.core.database import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    users = relationship(
        "User",
        back_populates="tenant",
    )

    documents = relationship(
        "Document",
        back_populates="tenant",
    )
