from datetime import UTC, datetime
from decimal import Decimal

from oblidog_integrations.integrations.ekartoteka.api import EkartotekaApi
from oblidog_integrations.integrations.ekartoteka.ekartoteka import Ekartoteka
from oblidog_integrations.integrations.ekartoteka.models import (
    FeePeriodsPage,
    MonthlyFeeItemsPage,
    PremisesPage,
    SettlementAccountsPage,
    UpdateDatesPage,
)


class FakeEkartotekaApi(EkartotekaApi):
    def _request_json(
        self, url: str, *, payload: dict[str, str] | None = None
    ) -> object:
        if url == self.URL_TOKEN:
            return {"token": "header.eyJ1c2VybmFtZSI6IjQyX2FjY291bnQifQ.signature"}
        if url == self.URL_ME:
            return {
                "Nazwa": "Jan Kowalski",
                "Email": "jan@example.com",
                "DaneKsiegowe": [7],
            }
        return {
            "count": 0,
            "next": None,
            "previous": None,
            "results": [],
        }


class FakeEkartoteka(Ekartoteka):
    def __init__(self, *, delta: Decimal, last_update: datetime | None) -> None:
        super().__init__({})
        self.delta = delta
        self.last_update = last_update

    def get_current_fees_sum(self) -> Decimal:
        return Decimal("123.45")

    def get_settlements_sum(self, year: int) -> Decimal:
        return self.delta

    def get_update_stamp(self) -> dict[str, datetime]:
        return {} if self.last_update is None else {"LI": self.last_update}


class FakeComponentsApi:
    def get_premises(self) -> PremisesPage:
        return PremisesPage.model_validate(
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [{"IdLok": 10, "kod": "A-10", "adres": "Testowa 10"}],
            }
        )

    def get_fee_periods(self, premises_id: int) -> FeePeriodsPage:
        assert premises_id == 10
        return FeePeriodsPage.model_validate(
            {
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "DataOd": "2026-09-01",
                        "DataDo": None,
                        "Stan": "ok",
                        "IdNal": 20,
                        "IdLok": 10,
                        "Naglowek": None,
                        "Stopka": None,
                        "Typ": "B",
                    },
                    {
                        "DataOd": "2026-08-01",
                        "DataDo": "2026-08-31",
                        "Stan": "ok",
                        "IdNal": 19,
                        "IdLok": 10,
                        "Naglowek": None,
                        "Stopka": None,
                        "Typ": "B",
                    },
                ],
            }
        )

    def get_monthly_fee_items(
        self, *, charge_id: int, premises_id: int
    ) -> MonthlyFeeItemsPage:
        assert (charge_id, premises_id) == (20, 10)
        return MonthlyFeeItemsPage.model_validate(
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "WspIle": 1,
                        "WspIleJM": None,
                        "Cena": 10,
                        "WspCena": 1,
                        "Nalicz": 10,
                        "is_sub": 0,
                        "Nazwa": "Czynsz",
                        "Ilosc": 1,
                        "JM": "mc",
                        "zaOkres": "",
                    }
                ],
            }
        )


def test_payment_status_marks_positive_balance_as_unpaid() -> None:
    client = FakeEkartoteka(
        delta=Decimal("10.0"),
        last_update=datetime.now(UTC),
    )

    status = client.get_payment_status()

    assert status.apartment_fee == Decimal("123.45")
    assert status.delta == Decimal("10.0")
    assert not status.paid
    assert status.force_unpaid == (datetime.now(UTC).day >= 25)


def test_payment_status_forces_unpaid_when_monthly_data_is_missing() -> None:
    client = FakeEkartoteka(delta=Decimal("-10.0"), last_update=None)

    status = client.get_payment_status()

    assert not status.paid
    assert status.force_unpaid


def test_settlement_response_has_pythonic_pydantic_fields() -> None:
    page = SettlementAccountsPage.model_validate(
        {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "IdKon": 1540355,
                    "Rok": 2026,
                    "Symbol": "204",
                    "Nazwa": "Rozrachunki z właścicielami",
                    "Ma": 4803.6,
                    "Wn": 4803.6,
                    "s": 0.0,
                }
            ],
        }
    )

    account = page.results[0]
    assert account.id == 1540355
    assert account.credit == Decimal("4803.6")
    assert account.model_dump(by_alias=True)["Nazwa"] == account.name


def test_fee_models_parse_dates_and_monetary_items() -> None:
    periods = FeePeriodsPage.model_validate(
        {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "DataOd": "2026-07-01",
                    "DataDo": None,
                    "Stan": "ok",
                    "IdNal": 1250689,
                    "IdLok": 918019,
                    "Naglowek": None,
                    "Stopka": None,
                    "Typ": "B",
                }
            ],
        }
    )
    items = MonthlyFeeItemsPage.model_validate(
        {
            "count": 1,
            "next": None,
            "previous": None,
            "results": [
                {
                    "WspIle": 1.0,
                    "WspIleJM": None,
                    "Cena": 0.64,
                    "WspCena": 1.0,
                    "Nalicz": 31.42,
                    "is_sub": 0,
                    "Nazwa": "Ciepło (opłata stała)",
                    "Ilosc": 49.1,
                    "JM": "m2",
                    "zaOkres": "",
                }
            ],
        }
    )

    assert periods.results[0].starts_on.isoformat() == "2026-07-01"
    assert items.results[0].amount == Decimal("31.42")


def test_low_level_client_returns_pydantic_models() -> None:
    api = FakeEkartotekaApi({})

    user = api.login()
    settlements = api.get_settlements(2026)

    assert user.accounting_id == 7
    assert settlements == SettlementAccountsPage(count=0, results=[])


def test_update_date_model_accepts_timestamps_and_missing_dates() -> None:
    page = UpdateDatesPage.model_validate(
        {
            "count": 2,
            "next": None,
            "previous": None,
            "results": [
                {"typ": "LI", "data": "2026-09-01T08:20:03.316000"},
                {"typ": "NRB", "data": None},
            ],
        }
    )

    assert page.results[0].updated_at.isoformat() == "2026-09-01T08:20:03.316000"
    assert page.results[1].updated_at is None


def test_current_fee_components_uses_the_active_period() -> None:
    client = Ekartoteka(api=FakeComponentsApi())  # type: ignore[arg-type]

    components = client.get_current_fee_components()

    assert len(components) == 1
    assert components[0].premises.code == "A-10"
    assert components[0].period.charge_id == 20
    assert components[0].items[0].name == "Czynsz"
