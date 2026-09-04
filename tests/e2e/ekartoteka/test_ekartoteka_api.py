"""Read-only E2E coverage for the live e-Kartoteka API.

Run with ``make test-e2e-ekartoteka``.  The target loads the untracked
``.env.ekartoteka`` file, so credentials are never committed to the repository.
"""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from oblidog_integrations.integrations.ekartoteka.api import EkartotekaApi
from oblidog_integrations.integrations.ekartoteka.ekartoteka import Ekartoteka

pytestmark = pytest.mark.ekartoteka_e2e


@pytest.fixture
def credentials() -> dict[str, str]:
    username = os.getenv("EKARTOTEKA_USERNAME")
    password = os.getenv("EKARTOTEKA_PASSWORD")
    if not username or not password:
        pytest.skip("Set EKARTOTEKA_USERNAME and EKARTOTEKA_PASSWORD to run E2E tests")
    return {"username": username, "password": password}


def test_fetches_active_fee_components(credentials: dict[str, str]) -> None:
    """The authenticated API exposes itemized charges for active premises."""
    api = EkartotekaApi(credentials)
    client = Ekartoteka(api=api)

    client.login()
    components = client.get_current_fee_components(
        datetime.now(ZoneInfo("Europe/Warsaw")).date()
    )

    assert api.user is not None
    assert components
    assert all(component.period.ends_on is None for component in components)
    assert all(component.items for component in components)
