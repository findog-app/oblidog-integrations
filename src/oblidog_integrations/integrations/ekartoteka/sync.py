from __future__ import annotations

import datetime
import json
import os

from findog_client import FindogClient

from oblidog_integrations.integrations.ekartoteka.ekartoteka import Ekartoteka


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def run() -> None:
    now = datetime.datetime.now(datetime.UTC)

    ekartoteka_client = Ekartoteka(
        credentials={
            "username": _required_env("EKARTOTEKA_USERNAME"),
            "password": _required_env("EKARTOTEKA_PASSWORD"),
        }
    )
    ekartoteka_client.login()
    result = ekartoteka_client.get_payment_status()
    components = ekartoteka_client.get_current_fee_components()

    print("Payment status:")
    print(result.model_dump_json(indent=2))
    print("Current fee components:")
    print(
        json.dumps(
            [component.model_dump(mode="json") for component in components],
            ensure_ascii=False,
            indent=2,
        )
    )

    with FindogClient(
        base_url=_required_env("OBLIDOG_URL"),
        api_key=_required_env("OBLIDOG_API_KEY"),
    ) as client:
        obligations = client.obligations.list(
            year=now.year,
            month=now.month,
            category_code=_required_env("OBLIDOG_CATEGORY_CODE"),
        )

        if obligations.count != 1:
            raise RuntimeError(
                f"Expected exactly one matching obligation, got {obligations.count}"
            )

        print(f"Found obligation: {obligations.data[0].key}")

        # obligation = obligations.data[0]
        # client.obligations.update(
        #     obligation.key,
        #     current_amount=str(record.amount),
        # )
        # client.obligations.append_note(
        #     obligation.key,
        #     f"Imported demo invoice {record.invoice_number}",
        # )
        # client.obligations.mark_ready(obligation.key)
