from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class DemoRecord:
    amount: Decimal
    invoice_number: str


def fetch() -> DemoRecord:
    """Return deterministic provider data for the proof of concept."""
    return DemoRecord(
        amount=Decimal(os.getenv("DEMO_AMOUNT", "42.00")),
        invoice_number=os.getenv("DEMO_INVOICE_NUMBER", "DEMO-001"),
    )
