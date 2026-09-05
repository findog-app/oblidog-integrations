from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Self

import pytest
from oblidog_client import ObligationLifecycle

from oblidog_integrations.integrations.nju import sync
from oblidog_integrations.integrations.nju.api import (
    NjuError,
    _require_authenticated_page,
    invoices_for_current_period,
    parse_invoices,
)
from oblidog_integrations.integrations.nju.models import NjuInvoice


def test_parse_invoices_extracts_the_portal_invoice_fields() -> None:
    invoices = parse_invoices(
        """
        <table>
          <tr id="id_abc-1">
            <td class="left-right-bg" data-title="nr dokumentu"><a id="doc-123">Faktura</a></td>
            <td class="left-right-bg" data-title="data wystawienia">01.09.2026</td>
            <td class="left-right-bg" data-title="termin płatności">15.09.2026</td>
            <td class="left-right-bg" data-title="kwota zapłacona">12,34 PLN</td>
            <td class="left-right-bg" data-title="do zapłaty">0,00 PLN</td>
            <td class="left-right-bg" data-title="za okres">09.2026</td>
            <td class="left-right-bg" data-title="status">zapłacona</td>
          </tr>
        </table>
        """
    )

    assert invoices == [
        NjuInvoice(
            document_id="123",
            issue_date=date(2026, 9, 1),
            due_date=date(2026, 9, 15),
            paid_amount=Decimal("12.34"),
            payable_amount=Decimal("0.00"),
            accounting_period="09.2026",
            status="zapłacona",
        )
    ]
    assert invoices[0].total_amount == Decimal("12.34")
    assert invoices[0].is_paid


def test_invoices_for_current_period_uses_the_portal_month_format() -> None:
    invoice = NjuInvoice(
        document_id="123",
        issue_date=date(2026, 9, 1),
        due_date=date(2026, 9, 15),
        paid_amount=Decimal(0),
        payable_amount=Decimal("12.34"),
        accounting_period="09.2026",
        status="niezapłacona",
    )

    assert invoices_for_current_period(
        [invoice], now=datetime(2026, 9, 5, tzinfo=UTC)
    ) == [invoice]
    assert (
        invoices_for_current_period([invoice], now=datetime(2026, 10, 5, tzinfo=UTC))
        == []
    )


def test_run_updates_and_readies_an_unpaid_current_invoice(monkeypatch) -> None:
    now = datetime.now(UTC)
    invoice = NjuInvoice(
        document_id="123",
        issue_date=now.date(),
        due_date=date(now.year, now.month, 15),
        paid_amount=Decimal("5.00"),
        payable_amount=Decimal("7.34"),
        accounting_period=now.strftime("%m.%Y"),
        status="niezapłacona",
    )
    updates: list[dict[str, object]] = []
    marked_ready: list[str] = []
    marked_paid: list[str] = []
    obligations = SimpleNamespace(
        list=lambda **_: SimpleNamespace(
            count=1,
            data=[
                SimpleNamespace(
                    key="NJU-2026-09",
                    lifecycle=ObligationLifecycle.COLLECTING_DATA,
                    current_amount=None,
                    issue_date=None,
                    due_date=None,
                )
            ],
        ),
        update=lambda key, **kwargs: updates.append({"key": key, **kwargs}),
        mark_ready=marked_ready.append,
        mark_paid=marked_paid.append,
        reopen=lambda _: None,
    )

    class FakeNjuClient:
        def __init__(self, **_: object) -> None:
            pass

        def fetch_invoices(self) -> list[NjuInvoice]:
            return [invoice]

    class FakeOblidogClient:
        def __init__(self, **_: object) -> None:
            self.obligations = obligations

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_: object) -> None:
            return None

    monkeypatch.setattr(sync, "NjuClient", FakeNjuClient)
    monkeypatch.setattr(sync, "OblidogClient", FakeOblidogClient)
    monkeypatch.setenv("NJU_PHONE", "phone")
    monkeypatch.setenv("NJU_PASSWORD", "password")
    monkeypatch.setenv("OBLIDOG_URL", "https://oblidog.example.com")
    monkeypatch.setenv("OBLIDOG_API_KEY", "api-key")
    monkeypatch.setenv("OBLIDOG_CATEGORY_CODE", "NJU")

    sync.run()

    assert updates == [
        {
            "key": "NJU-2026-09",
            "current_amount": "12.34",
            "issue_date": now.date(),
            "due_date": date(now.year, now.month, 15),
        }
    ]
    assert marked_ready == ["NJU-2026-09"]
    assert not marked_paid


def test_run_marks_a_fully_paid_current_invoice_as_paid(monkeypatch) -> None:
    now = datetime.now(UTC)
    invoice = NjuInvoice(
        document_id="123",
        issue_date=now.date(),
        due_date=date(now.year, now.month, 15),
        paid_amount=Decimal("12.34"),
        payable_amount=Decimal(0),
        accounting_period=now.strftime("%m.%Y"),
        status="zapłacona",
    )
    marked_paid: list[str] = []
    obligations = SimpleNamespace(
        list=lambda **_: SimpleNamespace(
            count=1,
            data=[
                SimpleNamespace(
                    key="NJU-2026-09",
                    lifecycle=ObligationLifecycle.COLLECTING_DATA,
                    current_amount=None,
                    issue_date=None,
                    due_date=None,
                )
            ],
        ),
        update=lambda *_args, **_kwargs: None,
        mark_ready=lambda _: None,
        mark_paid=marked_paid.append,
        reopen=lambda _: None,
    )

    class FakeNjuClient:
        def __init__(self, **_: object) -> None:
            pass

        def fetch_invoices(self) -> list[NjuInvoice]:
            return [invoice]

    class FakeOblidogClient:
        def __init__(self, **_: object) -> None:
            self.obligations = obligations

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_: object) -> None:
            return None

    monkeypatch.setattr(sync, "NjuClient", FakeNjuClient)
    monkeypatch.setattr(sync, "OblidogClient", FakeOblidogClient)
    monkeypatch.setenv("NJU_PHONE", "phone")
    monkeypatch.setenv("NJU_PASSWORD", "password")
    monkeypatch.setenv("OBLIDOG_URL", "https://oblidog.example.com")
    monkeypatch.setenv("OBLIDOG_API_KEY", "api-key")
    monkeypatch.setenv("OBLIDOG_CATEGORY_CODE", "NJU")

    sync.run()

    assert marked_paid == ["NJU-2026-09"]


def test_login_form_response_is_rejected_after_authentication() -> None:
    with pytest.raises(NjuError, match="rejected"):
        _require_authenticated_page(
            '<form><input name="phone-input"><input name="password-form"></form>'
        )


def test_reconcile_obligation_reopens_only_when_closed_data_or_status_changed() -> None:
    calls: list[str] = []
    obligation = SimpleNamespace(
        key="NJU-2026-09",
        lifecycle=ObligationLifecycle.READY,
        current_amount="12.34",
        issue_date=date(2026, 9, 1),
        due_date=date(2026, 9, 15),
    )

    class LifecycleEnforcingObligations:
        def reopen(self, key: str) -> None:
            assert obligation.lifecycle in {
                ObligationLifecycle.READY,
                ObligationLifecycle.PAID,
            }
            calls.append(f"reopen:{key}")
            obligation.lifecycle = ObligationLifecycle.COLLECTING_DATA

        def update(self, key: str, **_: object) -> None:
            assert obligation.lifecycle is ObligationLifecycle.COLLECTING_DATA
            calls.append(f"update:{key}")

        def mark_ready(self, key: str) -> None:
            assert obligation.lifecycle in {
                ObligationLifecycle.DRAFT,
                ObligationLifecycle.COLLECTING_DATA,
            }
            calls.append(f"ready:{key}")
            obligation.lifecycle = ObligationLifecycle.READY

        def mark_paid(self, key: str) -> None:
            assert obligation.lifecycle is ObligationLifecycle.READY
            calls.append(f"paid:{key}")
            obligation.lifecycle = ObligationLifecycle.PAID

    obligations = LifecycleEnforcingObligations()

    unchanged = sync._reconcile_obligation(
        obligations=obligations,
        obligation=obligation,
        total=Decimal("12.34"),
        issue_date=date(2026, 9, 1),
        due_date=date(2026, 9, 15),
        paid=False,
    )

    assert not unchanged
    assert not calls

    obligation.current_amount = "15.00"
    changed = sync._reconcile_obligation(
        obligations=obligations,
        obligation=obligation,
        total=Decimal("12.34"),
        issue_date=date(2026, 9, 1),
        due_date=date(2026, 9, 15),
        paid=True,
    )

    assert changed
    assert calls == [
        "reopen:NJU-2026-09",
        "update:NJU-2026-09",
        "ready:NJU-2026-09",
        "paid:NJU-2026-09",
    ]


def test_reconcile_obligation_marks_ready_before_paid_from_collecting_data() -> None:
    calls: list[str] = []
    obligation = SimpleNamespace(
        key="NJU-2026-09",
        lifecycle=ObligationLifecycle.COLLECTING_DATA,
        current_amount=None,
        issue_date=None,
        due_date=None,
    )

    class LifecycleEnforcingObligations:
        def update(self, key: str, **_: object) -> None:
            assert obligation.lifecycle is ObligationLifecycle.COLLECTING_DATA
            calls.append(f"update:{key}")

        def mark_ready(self, key: str) -> None:
            assert obligation.lifecycle is ObligationLifecycle.COLLECTING_DATA
            calls.append(f"ready:{key}")
            obligation.lifecycle = ObligationLifecycle.READY

        def mark_paid(self, key: str) -> None:
            assert obligation.lifecycle is ObligationLifecycle.READY
            calls.append(f"paid:{key}")
            obligation.lifecycle = ObligationLifecycle.PAID

    changed = sync._reconcile_obligation(
        obligations=LifecycleEnforcingObligations(),
        obligation=obligation,
        total=Decimal("12.34"),
        issue_date=date(2026, 9, 1),
        due_date=date(2026, 9, 15),
        paid=True,
    )

    assert changed
    assert calls == [
        "update:NJU-2026-09",
        "ready:NJU-2026-09",
        "paid:NJU-2026-09",
    ]


def test_reconcile_obligation_updates_issue_date_before_ready_from_draft() -> None:
    calls: list[str] = []
    obligation = SimpleNamespace(
        key="NJU-2026-09",
        lifecycle=ObligationLifecycle.DRAFT,
        current_amount="12.34",
        issue_date=None,
        due_date=date(2026, 9, 15),
    )

    class LifecycleEnforcingObligations:
        def update(self, key: str, **kwargs: object) -> None:
            assert obligation.lifecycle is ObligationLifecycle.DRAFT
            assert kwargs == {
                "current_amount": "12.34",
                "issue_date": date(2026, 9, 1),
                "due_date": date(2026, 9, 15),
            }
            calls.append(f"update:{key}")
            obligation.lifecycle = ObligationLifecycle.COLLECTING_DATA

        def mark_ready(self, key: str) -> None:
            assert obligation.lifecycle is ObligationLifecycle.COLLECTING_DATA
            calls.append(f"ready:{key}")
            obligation.lifecycle = ObligationLifecycle.READY

        def mark_paid(self, _: str) -> None:
            pytest.fail("An unpaid invoice must not be marked paid")

    changed = sync._reconcile_obligation(
        obligations=LifecycleEnforcingObligations(),
        obligation=obligation,
        total=Decimal("12.34"),
        issue_date=date(2026, 9, 1),
        due_date=date(2026, 9, 15),
        paid=False,
    )

    assert changed
    assert calls == ["update:NJU-2026-09", "ready:NJU-2026-09"]
