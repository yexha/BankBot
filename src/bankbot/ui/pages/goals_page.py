"""Savings goals: required monthly contribution and leftover-after-goals.

Goal contributions are reserved from leftover (in priority order) *before* the
investment math, so the invest page only ever offers money that's truly free.
"""
from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core import repository as repo
from ...core.budget import summarize
from ...core.goals import plan_goals
from ...core.money import format_money, to_cents


class GoalDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add savings goal")
        form = QFormLayout(self)
        self._name = QLineEdit()
        self._name.setPlaceholderText("e.g. Vehicle")
        self._target = QDoubleSpinBox()
        self._target.setRange(0, 100_000_000)
        self._target.setPrefix("$ ")
        self._target.setDecimals(2)
        self._saved = QDoubleSpinBox()
        self._saved.setRange(0, 100_000_000)
        self._saved.setPrefix("$ ")
        self._saved.setDecimals(2)
        self._date = QDateEdit()
        self._date.setCalendarPopup(True)
        self._date.setDate(QDate.currentDate().addYears(1))
        form.addRow("Name", self._name)
        form.addRow("Target amount", self._target)
        form.addRow("Already saved", self._saved)
        form.addRow("Target date", self._date)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def _validate_accept(self) -> None:
        if not self._name.text().strip():
            QMessageBox.warning(self, "Missing name", "Please enter a goal name.")
            return
        if self._target.value() <= 0:
            QMessageBox.warning(self, "Invalid amount", "Target must be greater than 0.")
            return
        self.accept()

    def values(self) -> dict:
        d = self._date.date()
        return {
            "name": self._name.text().strip(),
            "target_cents": to_cents(self._target.value()),
            "saved_cents": to_cents(self._saved.value()),
            "target_date": date(d.year(), d.month(), d.day()),
        }


class GoalsPage(QWidget):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        header.addWidget(QLabel("<h2>Savings goals</h2>"))
        header.addStretch(1)
        add = QPushButton("Add goal")
        add.clicked.connect(self._add_goal)
        header.addWidget(add)
        layout.addLayout(header)

        self._leftover_label = QLabel()
        self._leftover_label.setObjectName("goalsLeftover")
        self._leftover_label.setWordWrap(True)
        layout.addWidget(self._leftover_label)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Priority", "Goal", "Target", "By", "Needed / month", ""]
        )
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self._table, 1)

    def current_leftover_cents(self) -> int:
        year, month = repo.latest_month()
        return summarize(repo.transactions_for_month(year, month)).leftover_cents

    def leftover_after_goals_cents(self) -> int:
        goals = repo.list_goals()
        plan = plan_goals(goals, self.current_leftover_cents())
        return plan.leftover_after_goals_cents

    def refresh(self) -> None:
        currency = repo.get_setting("currency", "CAD") or "CAD"
        goals = repo.list_goals()
        leftover = self.current_leftover_cents()
        plan = plan_goals(goals, leftover)

        msg = (
            f"Leftover this month: <b>{format_money(leftover, currency)}</b> &nbsp;→&nbsp; "
            f"Reserved for goals: <b>{format_money(plan.total_funded_cents, currency)}</b> "
            f"&nbsp;→&nbsp; <b>Leftover after goals: "
            f"{format_money(plan.leftover_after_goals_cents, currency)}</b>"
        )
        if plan.underfunded and goals:
            msg += (
                "<br><span style='color:#c0392b'>⚠ Your leftover doesn't fully cover "
                "every goal's required monthly contribution. Lower-priority goals are "
                "only partially funded.</span>"
            )
        self._leftover_label.setText(msg)

        self._table.setRowCount(len(goals))
        for r, (goal, item) in enumerate(zip(goals, plan.items)):
            self._set(r, 0, str(r + 1))
            self._set(r, 1, goal.name)
            self._set(r, 2, format_money(goal.target_amount_cents, currency))
            self._set(r, 3, f"{goal.target_date:%b %Y}")
            needed = format_money(item.required_cents, currency)
            if not item.fully_funded:
                needed += f"  (funding {format_money(item.funded_cents, currency)})"
            self._set(r, 4, needed)
            self._table.setCellWidget(r, 5, self._row_actions(goal.id))

    def _row_actions(self, goal_id: int) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        up = QPushButton("▲")
        down = QPushButton("▼")
        delete = QPushButton("Delete")
        for b in (up, down):
            b.setFixedWidth(28)
        up.clicked.connect(lambda: self._move(goal_id, -1))
        down.clicked.connect(lambda: self._move(goal_id, +1))
        delete.clicked.connect(lambda: self._delete(goal_id))
        h.addWidget(up)
        h.addWidget(down)
        h.addWidget(delete)
        return w

    def _set(self, row: int, col: int, text: str) -> None:
        item = QTableWidgetItem(text)
        if col in (2, 4):
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._table.setItem(row, col, item)

    def _add_goal(self) -> None:
        dialog = GoalDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            v = dialog.values()
            currency = repo.get_setting("currency", "CAD") or "CAD"
            repo.add_goal(v["name"], v["target_cents"], v["target_date"],
                          v["saved_cents"], currency)
            self.refresh()
            self.dataChanged.emit()

    def _move(self, goal_id: int, direction: int) -> None:
        repo.move_goal(goal_id, direction)
        self.refresh()
        self.dataChanged.emit()

    def _delete(self, goal_id: int) -> None:
        repo.delete_goal(goal_id)
        self.refresh()
        self.dataChanged.emit()
