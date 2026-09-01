from __future__ import annotations

import os

from findog_client import FindogClient

from oblidog_integrations.integrations.ekartoteka.provider import EkartotekaProvider


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def run() -> None:
    charge = EkartotekaProvider().fetch_current_charge()

    with FindogClient(
        base_url=_required_env("OBLIDOG_URL"),
        api_key=_required_env("OBLIDOG_API_KEY"),
    ) as client:
        obligations = client.obligations.list(
            year=charge.period.year,
            month=charge.period.month,
            category_code=_required_env("OBLIDOG_CATEGORY_CODE"),
        )

        if obligations.count != 1:
            raise RuntimeError(
                f"Expected exactly one matching obligation, got {obligations.count}"
            )

        obligation = obligations.data[0]
        client.obligations.update(
            obligation.key,
            current_amount=str(charge.total_amount),
            due_date=charge.due_date,
        )

        for component in charge.components:
            client.obligations.upsert_component(
                obligation.key,
                type=component.code,
                label=component.label,
                amount=str(component.amount),
                source="ekartoteka",
            )

        if charge.external_id:
            client.obligations.append_note(
                obligation.key,
                f"Imported e-kartoteka charge {charge.external_id}",
            )

        client.obligations.mark_ready(obligation.key)
