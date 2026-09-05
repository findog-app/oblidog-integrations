"""Synchronize one NJU Mobile account with one Oblidog category."""

from __future__ import annotations

import os
from datetime import UTC, datetime

import structlog
from oblidog_client import OblidogClient

from oblidog_integrations.integrations.nju.api import (
    NjuClient,
    invoices_for_current_period,
)

logger = structlog.get_logger(__name__)


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def run() -> None:
    """Synchronize the current NJU invoice period for one configured account."""
    now = datetime.now(UTC)
    account_name = os.getenv("NJU_ACCOUNT_NAME", "nju")
    invoices = invoices_for_current_period(
        NjuClient(
            phone=_required_env("NJU_PHONE"),
            password=_required_env("NJU_PASSWORD"),
        ).fetch_invoices(),
        now=now,
    )
    if not invoices:
        logger.info(
            "nju_invoices_absent", account=account_name, period=now.strftime("%m.%Y")
        )
        return

    category_code = _required_env("OBLIDOG_CATEGORY_CODE")
    with OblidogClient(
        base_url=_required_env("OBLIDOG_URL"),
        api_key=_required_env("OBLIDOG_API_KEY"),
    ) as oblidog:
        obligations = oblidog.obligations.list(
            year=now.year,
            month=now.month,
            category_code=category_code,
        )
        if obligations.count != 1:
            raise RuntimeError(
                f"Expected exactly one NJU obligation for {category_code}, got "
                f"{obligations.count}"
            )
        obligation = obligations.data[0]
        total = sum((invoice.total_amount for invoice in invoices), start=0)
        due_date = min(invoice.due_date for invoice in invoices)
        oblidog.obligations.update(
            obligation.key,
            current_amount=str(total),
            due_date=due_date,
        )
        paid = all(invoice.is_paid for invoice in invoices)
        if paid:
            oblidog.obligations.mark_paid(obligation.key)
        else:
            oblidog.obligations.mark_ready(obligation.key)

    logger.info(
        "nju_obligation_synced",
        account=account_name,
        obligation_key=obligation.key,
        invoice_count=len(invoices),
        current_amount=str(total),
        due_date=due_date.isoformat(),
        paid=paid,
    )
