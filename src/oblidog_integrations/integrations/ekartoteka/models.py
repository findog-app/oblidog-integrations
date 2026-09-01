from __future__ import annotations

import datetime
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ChargeComponent:
    code: str
    label: str
    amount: Decimal


@dataclass(frozen=True, slots=True)
class MonthlyCharge:
    period: datetime.date
    total_amount: Decimal
    due_date: datetime.date | None
    external_id: str | None
    components: tuple[ChargeComponent, ...]
