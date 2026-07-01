"""Database engine, session factory, and first-run bootstrap/seeding."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .. import config
from .models import Base, Category, Rule, Setting

_engine: Engine | None = None
_Session: sessionmaker[Session] | None = None


def init_engine(db_file: Path | str | None = None) -> Engine:
    """Create (or recreate) the engine and ensure schema + seed data exist."""
    global _engine, _Session
    path = Path(db_file) if db_file is not None else config.db_path()
    _engine = create_engine(f"sqlite:///{path}", future=True)
    _Session = sessionmaker(bind=_engine, future=True, expire_on_commit=False)
    Base.metadata.create_all(_engine)
    with session_scope() as s:
        _seed(s)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        init_engine()
    assert _engine is not None
    return _engine


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session context; rolls back on error."""
    if _Session is None:
        init_engine()
    assert _Session is not None
    session = _Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_data() -> None:
    """Drop and recreate all tables (Settings → Clear/reset stored data)."""
    engine = get_engine()
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with session_scope() as s:
        _seed(s)


def clear_transactions() -> None:
    """Delete imported statements and transactions only.

    Goals, settings (currency, slider %s, limits) and learned categorization rules
    are kept, so the user can wipe imported data and re-import without losing setup.
    """
    from sqlalchemy import delete

    from .models import Statement, Transaction

    with session_scope() as s:
        s.execute(delete(Transaction))
        s.execute(delete(Statement))


def _seed(session: Session) -> None:
    """Idempotently seed default settings, categories, and builtin rules."""
    from .categorize.rules import DEFAULT_CATEGORIES, default_rule_rows

    # Settings (only fill missing keys so user edits survive).
    existing = {row.key for row in session.scalars(select(Setting)).all()}
    for key, value in config.DEFAULT_SETTINGS.items():
        if key not in existing:
            session.add(Setting(key=key, value=value))

    if session.scalar(select(Category).limit(1)) is None:
        for name, ess in DEFAULT_CATEGORIES:
            session.add(Category(name=name, default_essential_want=ess, is_system=True))

    if session.scalar(select(Rule).limit(1)) is None:
        for row in default_rule_rows():
            session.add(Rule(**row))
