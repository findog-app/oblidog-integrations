from __future__ import annotations

import argparse
from collections.abc import Callable

from oblidog_integrations.integrations.demo import run as run_demo

IntegrationRunner = Callable[[], None]

INTEGRATIONS: dict[str, IntegrationRunner] = {
    "demo": run_demo,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an Oblidog integration")
    parser.add_argument("integration", choices=sorted(INTEGRATIONS))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    INTEGRATIONS[args.integration]()
