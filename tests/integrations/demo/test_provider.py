from decimal import Decimal

from oblidog_integrations.integrations.demo.provider import fetch


def test_fetch_uses_defaults(monkeypatch) -> None:
    monkeypatch.delenv("DEMO_AMOUNT", raising=False)
    monkeypatch.delenv("DEMO_INVOICE_NUMBER", raising=False)

    record = fetch()

    assert record.amount == Decimal("42.00")
    assert record.invoice_number == "DEMO-001"
