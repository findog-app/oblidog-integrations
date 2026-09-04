"""Publication of e-Kartoteka snapshots as Oblidog category data."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from findog_client import FindogClient
from findog_client.generated.errors import UnexpectedStatus

from oblidog_integrations.integrations.ekartoteka.ekartoteka import (
    Ekartoteka,
    SettlementSnapshot,
)


@dataclass(frozen=True)
class SnapshotExportResult:
    """Outcome of comparing and exporting one e-Kartoteka snapshot."""

    snapshot: SettlementSnapshot
    created: bool


def _latest_data(findog: FindogClient, category_code: str) -> dict[str, object] | None:
    try:
        return findog.category_data.latest(category_code).data.to_dict()
    except UnexpectedStatus as error:
        if error.status_code == 404:
            return None
        raise


def export_snapshot(
    *,
    ekartoteka: Ekartoteka,
    findog: FindogClient,
    category_code: str,
    year: int,
) -> SnapshotExportResult:
    """Create a category-data observation when the snapshot has changed.

    Args:
        ekartoteka: Authenticated provider facade used to fetch the snapshot.
        findog: Authenticated Oblidog client used to read and create data.
        category_code: Oblidog category that owns the observation.
        year: Settlement year included in the snapshot.

    Returns:
        The generated snapshot and whether a new observation was created.

    Raises:
        UnexpectedStatus: If reading the latest category data fails for a
            reason other than a missing record.
    """
    snapshot = ekartoteka.get_settlement_snapshot(year)
    data = snapshot.model_dump(mode="json")
    if _latest_data(findog, category_code) == data:
        return SnapshotExportResult(snapshot=snapshot, created=False)

    findog.category_data.create(
        category_code,
        observed_at=datetime.now(UTC),
        data=data,
        source="ekartoteka",
    )
    return SnapshotExportResult(snapshot=snapshot, created=True)
