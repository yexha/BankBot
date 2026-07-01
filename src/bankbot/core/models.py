"""SQLAlchemy ORM models. Money columns are integer cents.

Schema (v1):
  statements    one row per imported file (dedupe of whole files via file_hash)
  transactions  parsed rows; dedupe_hash unique across re-uploads
  categories    category definitions + default Essential/Want
  rules         categorization rules AND learned payee memory
  goals         savings goals
  settings      key/value app settings
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String)
    bank_profile: Mapped[str] = mapped_column(String, default="generic")
    file_hash: Mapped[str] = mapped_column(String, index=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    txn_count: Mapped[int] = mapped_column(Integer, default=0)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="statement")


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (UniqueConstraint("dedupe_hash", name="uq_txn_dedupe"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    statement_id: Mapped[int | None] = mapped_column(ForeignKey("statements.id"))
    txn_date: Mapped[date] = mapped_column(Date, index=True)
    description: Mapped[str] = mapped_column(String)            # raw
    normalized_desc: Mapped[str] = mapped_column(String, default="")
    amount_cents: Mapped[int] = mapped_column(Integer)         # always positive magnitude
    currency: Mapped[str] = mapped_column(String, default="CAD")
    direction: Mapped[str] = mapped_column(String)             # 'debit' | 'credit'
    category: Mapped[str | None] = mapped_column(String)
    # 'essential' | 'want' | 'income' | 'ignore' | None
    essential_want: Mapped[str | None] = mapped_column(String)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    is_income: Mapped[bool] = mapped_column(Boolean, default=False)
    # 'auto' | 'needs_review' | 'confirmed'
    review_status: Mapped[str] = mapped_column(String, default="auto", index=True)
    source_rule_id: Mapped[int | None] = mapped_column(ForeignKey("rules.id"))
    dedupe_hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    statement: Mapped[Statement | None] = relationship(back_populates="transactions")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    default_essential_want: Mapped[str] = mapped_column(String, default="want")
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)


class Rule(Base):
    """Categorization rule and learned payee memory in one mechanism.

    A user confirming an ambiguous transaction inserts a ``source='user_confirmed'``
    ``match_type='exact_payee'`` rule so the same payee auto-classifies next time.
    Higher ``priority`` wins; user-confirmed rules are seeded above builtins.
    """

    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_type: Mapped[str] = mapped_column(String)   # 'keyword' | 'regex' | 'exact_payee'
    pattern: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    essential_want: Mapped[str] = mapped_column(String)  # 'essential' | 'want' | 'ignore'
    is_recurring_bill: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=100)
    source: Mapped[str] = mapped_column(String, default="builtin")  # 'builtin'|'user_confirmed'
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String)
    target_amount_cents: Mapped[int] = mapped_column(Integer)
    target_date: Mapped[date] = mapped_column(Date)
    current_saved_cents: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[int] = mapped_column(Integer, default=0)  # lower = higher priority
    currency: Mapped[str] = mapped_column(String, default="CAD")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, default="")
