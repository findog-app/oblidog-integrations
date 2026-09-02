from __future__ import annotations

import argparse
from collections.abc import Callable

from oblidog_integrations.integrations.demo import run as run_demo
from oblidog_integrations.integrations.ekartoteka import run as run_ekartoteka

IntegrationRunner = Callable[[], None]

INTEGRATIONS: dict[str, IntegrationRunner] = {
    "demo": run_demo,
    "ekartoteka": run_ekartoteka,
}



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an Oblidog integration")
    parser.add_argument("integration", choices=sorted(INTEGRATIONS))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    INTEGRATIONS[args.integration]()


if __name__ == "__main__":
    main()
