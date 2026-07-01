"""Import + categorization services (no Qt) used by the UI worker thread."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from sqlalchemy import select

from .categorize.engine import classify_transactions
from .db import session_scope
from .models import Rule, Statement, Transaction
from .parsing.extractor import ExtractResult, extract_file

ProgressCb = Callable[[int, int, str], None]  # (done, total, message)


@dataclass
class FileOutcome:
    filename: str
    added: int = 0
    duplicates: int = 0
    error: str | None = None


@dataclass
class ImportReport:
    files: list[FileOutcome] = field(default_factory=list)

    @property
    def total_added(self) -> int:
        return sum(f.added for f in self.files)

    @property
    def total_duplicates(self) -> int:
        return sum(f.duplicates for f in self.files)

    @property
    def errors(self) -> list[FileOutcome]:
        return [f for f in self.files if f.error]


def import_files(
    paths: Sequence[str], currency: str = "CAD", progress: ProgressCb | None = None
) -> ImportReport:
    """Parse and store each file, deduplicating, then recategorize everything."""
    report = ImportReport()
    total = len(paths)
    any_added = False
    for idx, path in enumerate(paths, start=1):
        if progress:
            progress(idx - 1, total, f"Reading {path}…")
        result = extract_file(path, currency=currency)
        outcome = _store_result(result)
        report.files.append(outcome)
        any_added = any_added or outcome.added > 0
        if progress:
            progress(idx, total, f"Imported {result.filename}")
    if any_added:
        if progress:
            progress(total, total, "Categorizing transactions…")
        recategorize_all()
    return report


def _store_result(result: ExtractResult) -> FileOutcome:
    outcome = FileOutcome(filename=result.filename, error=result.error)
    if not result.ok:
        return outcome
    with session_scope() as s:
        statement = Statement(
            filename=result.filename,
            bank_profile=result.bank_profile,
            file_hash=result.file_hash,
        )
        s.add(statement)
        s.flush()
        existing = set(
            s.scalars(
                select(Transaction.dedupe_hash).where(
                    Transaction.dedupe_hash.in_([t.dedupe_hash for t in result.transactions])
                )
            ).all()
        )
        seen_in_file: set[str] = set()
        for t in result.transactions:
            if t.dedupe_hash in existing or t.dedupe_hash in seen_in_file:
                outcome.duplicates += 1
                continue
            seen_in_file.add(t.dedupe_hash)
            s.add(
                Transaction(
                    statement_id=statement.id,
                    txn_date=t.txn_date,
                    description=t.description,
                    normalized_desc=t.normalized_desc,
                    amount_cents=t.amount_cents,
                    currency=t.currency,
                    direction=t.direction,
                    dedupe_hash=t.dedupe_hash,
                )
            )
            outcome.added += 1
        statement.txn_count = outcome.added
    return outcome


def recategorize_all() -> None:
    """Re-run categorization over all non-user-confirmed transactions.

    User-confirmed transactions (``review_status == 'confirmed'``) are preserved.
    Income detection runs across the full history for reliable recurrence.
    """
    with session_scope() as s:
        rules = list(s.scalars(select(Rule).order_by(Rule.priority.desc())).all())
        txns = list(s.scalars(select(Transaction).order_by(Transaction.txn_date)).all())
        classifications = classify_transactions(txns, rules)
        for txn, c in zip(txns, classifications):
            if txn.review_status == "confirmed":
                continue
            txn.category = c.category
            txn.essential_want = c.essential_want
            txn.confidence = c.confidence
            txn.is_income = c.is_income
            txn.review_status = c.review_status
            txn.source_rule_id = c.source_rule_id
