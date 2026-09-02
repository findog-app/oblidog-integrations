"""Business operations built on the typed e-Kartoteka API client."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from pydantic import BaseModel

from oblidog_integrations.integrations.ekartoteka.api import (
    EkartotekaApi,
    EkartotekaError,
    NotInitializedError,
)
from oblidog_integrations.integrations.ekartoteka.models import (
    FeePeriod,
    MonthlyFeeItem,
    Premises,
)


class EkartotekaResult(BaseModel):
    """Apartment fee and settlement summary returned by ``get_payment_status``."""

    apartment_fee: Decimal
    delta: Decimal
    paid: bool
    force_unpaid: bool
    update_dates: dict[str, datetime]


class CurrentFeeComponents(BaseModel):
    """Itemized charges for the active billing period of one premises."""

    premises: Premises
    period: FeePeriod
    items: list[MonthlyFeeItem]


class Ekartoteka:
    """Apply Oblidog payment-status rules to e-Kartoteka data."""

    def __init__(
        self,
        credentials: dict[str, str] | None = None,
        *,
        api: EkartotekaApi | None = None,
    ) -> None:
        self.api = api or EkartotekaApi(credentials or {})

    def login(self) -> None:
        """Authenticate the underlying API client."""
        self.api.login()

    def get_settlements_sum(self, year: int) -> Decimal:
        """Calculate the balance (debit minus credit) for ``year``."""
        try:
            return sum(
                (
                    item.debit - item.credit
                    for item in self.api.get_settlements(year).results
                ),
                Decimal(0),
            )
        except (TypeError, ValueError) as error:
            raise EkartotekaError(
                "Invalid settlements data from e-Kartoteka"
            ) from error

    def get_current_fees_sum(self) -> Decimal:
        """Return the current gross monthly fee total."""
        return self.api.get_current_fee_total().gross_amount

    def get_update_stamp(self) -> dict[str, datetime]:
        """Return dates for categories relevant to payment-status rules."""
        monitored_categories = {"DK", "DKL", "SRC", "LI", "NL", "NRB", "STL"}
        return {
            item.category: datetime.combine(
                item.updated_at.date(), datetime.min.time(), tzinfo=UTC
            )
            for item in self.api.get_update_dates().results
            if item.category in monitored_categories and item.updated_at is not None
        }

    def get_current_fee_components(self) -> list[CurrentFeeComponents]:
        """Return itemized charges for every premises with an active period."""
        components = []
        for premises in self.api.get_premises().results:
            period = next(
                (
                    candidate
                    for candidate in self.api.get_fee_periods(premises.id).results
                    if candidate.ends_on is None
                ),
                None,
            )
            if period is None:
                continue
            items = self.api.get_monthly_fee_items(
                charge_id=period.charge_id,
                premises_id=premises.id,
            )
            components.append(
                CurrentFeeComponents(
                    premises=premises,
                    period=period,
                    items=items.results,
                )
            )
        return components

    def get_payment_status(self) -> EkartotekaResult:
        """Aggregate the current monthly fee and settlement state."""
        now = datetime.now(UTC)
        apartment_fee = self.get_current_fees_sum()
        delta = self.get_settlements_sum(now.year)
        dates = self.get_update_stamp()
        last_li_update = dates.get("LI")
        if last_li_update is None or (now.year, now.month) != (
            last_li_update.year,
            last_li_update.month,
        ):
            return EkartotekaResult(
                apartment_fee=apartment_fee,
                delta=delta,
                paid=False,
                force_unpaid=True,
                update_dates=dates,
            )
        return EkartotekaResult(
            apartment_fee=apartment_fee,
            delta=delta,
            paid=delta <= Decimal(0),
            force_unpaid=now.day >= 25,
            update_dates=dates,
        )


__all__ = [
    "CurrentFeeComponents",
    "Ekartoteka",
    "EkartotekaError",
    "EkartotekaResult",
    "NotInitializedError",
]
