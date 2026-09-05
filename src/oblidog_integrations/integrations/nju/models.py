"""Validated provider models for NJU Mobile invoices."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class NjuInvoice:
    """One invoice shown in the NJU Mobile customer portal."""

    document_id: str
    issue_date: date
    due_date: date
    paid_amount: Decimal
    payable_amount: Decimal
    accounting_period: str
    status: str

    @property
    def total_amount(self) -> Decimal:
        """Return the complete invoice amount, including a settled amount."""
        return self.paid_amount + self.payable_amount

    @property
    def is_paid(self) -> bool:
        """Whether the portal marks this invoice as paid."""
        return self.status.casefold() == "zapłacona"
