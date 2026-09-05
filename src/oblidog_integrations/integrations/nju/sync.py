"""Synchronize one NJU Mobile account with one Oblidog category."""

from __future__ import annotations

import os
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

import structlog
from oblidog_client import OblidogClient, ObligationLifecycle

from oblidog_integrations.integrations.nju.api import (
    NjuClient,
    invoices_for_current_period,
)

logger = structlog.get_logger(__name__)

_EDITABLE_LIFECYCLES = {
    ObligationLifecycle.DRAFT,
    ObligationLifecycle.COLLECTING_DATA,
}
_REOPENABLE_LIFECYCLES = {
    ObligationLifecycle.READY,
    ObligationLifecycle.PAID,
}


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _has_current_values(
    obligation: Any, *, total: Decimal, issue_date: date, due_date: date
) -> bool:
    try:
        current_amount = Decimal(str(obligation.current_amount))
    except (InvalidOperation, ValueError):
        return False
    return (
        current_amount == total
        and obligation.issue_date == issue_date
        and obligation.due_date == due_date
    )


def _reconcile_obligation(
    *,
    obligations: Any,
    obligation: Any,
    total: Decimal,
    issue_date: date,
    due_date: date,
    paid: bool,
) -> bool:
    """Apply NJU data while respecting Oblidog's obligation lifecycle."""
    values_current = _has_current_values(
        obligation, total=total, issue_date=issue_date, due_date=due_date
    )
    lifecycle = obligation.lifecycle
    target_lifecycle = ObligationLifecycle.PAID if paid else ObligationLifecycle.READY

    if lifecycle in _REOPENABLE_LIFECYCLES:
        if values_current and lifecycle == target_lifecycle:
            return False
        obligations.reopen(obligation.key)
        if not values_current:
            obligations.update(
                obligation.key,
                current_amount=str(total),
                issue_date=issue_date,
                due_date=due_date,
            )
    elif lifecycle in _EDITABLE_LIFECYCLES:
        if not values_current:
            obligations.update(
                obligation.key,
                current_amount=str(total),
                issue_date=issue_date,
                due_date=due_date,
            )
    else:
        logger.warning(
            "nju_obligation_skipped",
            obligation_key=obligation.key,
            lifecycle=lifecycle.value,
            reason="lifecycle_not_editable_or_reopenable",
        )
        return False

    obligations.mark_ready(obligation.key)
    if paid:
        obligations.mark_paid(obligation.key)
    return True


def run() -> None:
    """Synchronize the current NJU invoice period for one configured account."""
    now = datetime.now(ZoneInfo("Europe/Warsaw"))
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
        issue_date = min(invoice.issue_date for invoice in invoices)
        due_date = min(invoice.due_date for invoice in invoices)
        paid = all(invoice.is_paid for invoice in invoices)
        changed = _reconcile_obligation(
            obligations=oblidog.obligations,
            obligation=obligation,
            total=total,
            issue_date=issue_date,
            due_date=due_date,
            paid=paid,
        )

    logger.info(
        "nju_obligation_synced",
        account=account_name,
        obligation_key=obligation.key,
        invoice_count=len(invoices),
        current_amount=str(total),
        issue_date=issue_date.isoformat(),
        due_date=due_date.isoformat(),
        paid=paid,
        changed=changed,
    )
