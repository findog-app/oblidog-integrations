"""JSON Schema generator for the e-Kartoteka category-data snapshot."""

from __future__ import annotations

import json
from typing import Any

from oblidog_integrations.integrations.ekartoteka.ekartoteka import (
    MVP_ACCOUNT_SYMBOLS,
    MVP_UPDATE_CATEGORIES,
)

MVP_ACCOUNT_TITLES = {
    "204": "Rozrachunki z właścicielami",
    "206": "Fundusz remontowy",
    "210": "Odsetki właścicieli",
}


def settlement_snapshot_schema() -> dict[str, Any]:
    """Return the JSON Schema accepted by Oblidog Ledger for this snapshot."""
    properties: dict[str, dict[str, Any]] = {
        "year": {
            "type": "integer",
            "title": "Settlement year",
            "description": "Year requested from e-Kartoteka.",
        }
    }
    for symbol in MVP_ACCOUNT_SYMBOLS:
        for field, label in (
            ("credit", "Ma"),
            ("debit", "Wn"),
            ("balance", "Saldo"),
        ):
            properties[f"account_{symbol}_{field}"] = {
                "anyOf": [{"type": "number"}, {"type": "null"}],
                "title": f"{MVP_ACCOUNT_TITLES[symbol]} — {label}",
            }
    for category in MVP_UPDATE_CATEGORIES:
        properties[f"update_{category.lower()}_at"] = {
            "anyOf": [
                {"type": "string", "format": "date-time"},
                {"type": "null"},
            ],
            "title": f"{category} updated at",
        }

    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def main() -> None:
    """Print the schema for pasting into Oblidog Ledger."""
    print(json.dumps(settlement_snapshot_schema(), indent=2))


if __name__ == "__main__":
    main()
