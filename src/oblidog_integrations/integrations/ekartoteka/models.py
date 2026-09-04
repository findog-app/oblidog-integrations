"""Typed representations of e-Kartoteka API responses.

The service uses Polish, PascalCase keys.  Public model attributes use English
snake_case names; aliases keep the wire format an implementation detail.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class EkartotekaModel(BaseModel):
    """Base model accepting the extra fields occasionally added by the API."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")


class Page[ItemT](EkartotekaModel):
    count: int
    next: str | None = None
    previous: str | None = None
    results: list[ItemT]


class SettlementYear(EkartotekaModel):
    year: int = Field(alias="Rok")
    purchased: bool = Field(alias="wykupione")


class TokenResponse(EkartotekaModel):
    token: str


class AuthenticatedUser(EkartotekaModel):
    full_name: str = Field(alias="Nazwa")
    email: str = Field(alias="Email")
    accounting_ids: list[int] = Field(alias="DaneKsiegowe")

    @property
    def accounting_id(self) -> int:
        try:
            return self.accounting_ids[0]
        except IndexError as error:
            raise ValueError("User response has no accounting identifier") from error


class SettlementAccount(EkartotekaModel):
    id: int = Field(alias="IdKon")
    year: int = Field(alias="Rok")
    symbol: str = Field(alias="Symbol")
    name: str = Field(alias="Nazwa")
    credit: Decimal = Field(alias="Ma")
    debit: Decimal = Field(alias="Wn")
    balance: Decimal = Field(alias="s")


class AnnualLedgerEntry(EkartotekaModel):
    amount_due: Decimal = Field(alias="DoZaplaty")
    amount_paid: Decimal = Field(alias="Zaplacono")
    month: int = Field(alias="Mc")
    overpayment: Decimal = Field(alias="Nadplata")
    arrears: Decimal = Field(alias="Zaleglosc")
    limit_months: bool = Field(alias="islimitMonths")
    balance: Decimal = Field(alias="s")


class Premises(EkartotekaModel):
    id: int = Field(alias="IdLok")
    code: str = Field(alias="kod")
    address: str = Field(alias="adres")


class FeePeriod(EkartotekaModel):
    starts_on: date = Field(alias="DataOd")
    ends_on: date | None = Field(alias="DataDo")
    status: str = Field(alias="Stan")
    charge_id: int = Field(alias="IdNal")
    premises_id: int = Field(alias="IdLok")
    header: str | None = Field(alias="Naglowek")
    footer: str | None = Field(alias="Stopka")
    type: str = Field(alias="Typ")


class BankAccount(EkartotekaModel):
    """Bank-account record; its fields are provider-specific and undocumented."""


class MonthlyFeeItem(EkartotekaModel):
    quantity_factor: Decimal = Field(alias="WspIle")
    quantity_factor_unit: str | None = Field(alias="WspIleJM")
    unit_price: Decimal = Field(alias="Cena")
    price_factor: Decimal = Field(alias="WspCena")
    amount: Decimal = Field(alias="Nalicz")
    is_subitem: bool = Field(alias="is_sub")
    name: str = Field(alias="Nazwa")
    quantity: Decimal = Field(alias="Ilosc")
    unit: str = Field(alias="JM")
    period_description: str = Field(alias="zaOkres")


class CurrentFeeTotal(EkartotekaModel):
    gross_amount: Decimal = Field(alias="Brutto")


class UpdateDate(EkartotekaModel):
    category: str = Field(alias="typ")
    updated_at: datetime | None = Field(alias="data")


SettlementAccountsPage = Page[SettlementAccount]
PremisesPage = Page[Premises]
FeePeriodsPage = Page[FeePeriod]
BankAccountsPage = Page[BankAccount]
MonthlyFeeItemsPage = Page[MonthlyFeeItem]
UpdateDatesPage = Page[UpdateDate]
