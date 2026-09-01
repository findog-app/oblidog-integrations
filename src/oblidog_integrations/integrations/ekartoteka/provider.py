from __future__ import annotations

from oblidog_integrations.integrations.ekartoteka.models import MonthlyCharge


class EkartotekaProvider:
    """Adapter for e-kartoteka.

    The public portal does not expose API documentation. The concrete HTTP
    implementation will be added after capturing the requests made by the
    web/mobile client. Keep all provider-specific auth and payload parsing in
    this module so the Oblidog sync remains independent of e-kartoteka details.
    """

    def fetch_current_charge(self) -> MonthlyCharge:
        raise NotImplementedError(
            "e-kartoteka HTTP endpoints have not been mapped yet"
        )
