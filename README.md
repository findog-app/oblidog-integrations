# oblidog-integrations

Batch and one-shot integrations for Oblidog.

The repository is a monorepo for integrations that run periodically, fetch data from an external provider, synchronize it through `oblidog-client`, and exit. Long-running services such as mail ingestion should live separately.

## Structure

```text
src/oblidog_integrations/
├── cli.py
└── integrations/
    └── demo/
        ├── provider.py
        └── sync.py
```

Each integration owns its provider-specific code and exposes a parameterless `run()` function. The central CLI only registers and dispatches integrations.

## Development

Python 3.12 and `uv` are used for dependency management.

```bash
uv sync
uv run ruff check .
uv run pytest
```

The same common commands are available through `make`:

```bash
make sync
make check
make run-ekartoteka
make print-ekartoteka-schema
```

`make print-ekartoteka-schema` prints the JSON Schema for the flat e-Kartoteka
category-data record. Paste it into the category-schema import in Oblidog Ledger.

Before running e-Kartoteka for the first time, prepare its local configuration:

```bash
cp .env.ekartoteka.example .env.ekartoteka
```

Set `EKARTOTEKA_USERNAME`, `EKARTOTEKA_PASSWORD`, `OBLIDOG_URL`,
`OBLIDOG_API_KEY`, and `OBLIDOG_CATEGORY_CODE` in that file. Running
`make run-ekartoteka` prints and creates a category-data observation containing
the e-Kartoteka settlement snapshot.

Logs use a readable console format by default. Set `OBLIDOG_LOG_FORMAT=json`
to emit one JSON object per log event for systemd or a log collector.

Run the proof-of-concept integration with:

```bash
OBLIDOG_URL=https://oblidog.example.com \
OBLIDOG_API_KEY=... \
OBLIDOG_CATEGORY_CODE=DEMO \
uv run oblidog-integrations demo
```

Optional demo provider values:

```text
DEMO_AMOUNT=42.00
DEMO_INVOICE_NUMBER=DEMO-001
```

The demo integration expects exactly one matching obligation for the current month. It updates its amount, appends an import note, and marks it ready.

## Docker

A single, non-root production image contains all batch integrations. The
integration name is passed as the container argument. Builds use the locked
dependencies in `uv.lock`; `.env` files and credentials are excluded from the
build context.

```bash
docker build -t oblidog-integrations:local .
docker run --rm oblidog-integrations:local --help
```

The published image is `ghcr.io/oblidog/oblidog-integrations:vX.Y.Z`. Only
immutable release tags are published—there is no `latest`, `main`, or `edge`
tag.

To run e-Kartoteka through Compose, create the local credential file first:

```bash
cp .env.ekartoteka.example .env.ekartoteka
# edit .env.ekartoteka with the required credentials and Oblidog settings
printf 'OBLIDOG_INTEGRATIONS_VERSION=v0.1.0\n' > .env
docker compose run --rm ekartoteka
```

Upgrade by changing `OBLIDOG_INTEGRATIONS_VERSION` to the selected published
tag and pulling it before the next run. Roll back by setting it to an earlier
tag; Compose never uses a mutable image tag.

```bash
OBLIDOG_INTEGRATIONS_VERSION=v0.2.0 docker compose pull ekartoteka
OBLIDOG_INTEGRATIONS_VERSION=v0.2.0 docker compose run --rm ekartoteka
```

Future integrations are additional Compose services using the same image with
their own command and `env_file`.

### e-Kartoteka scheduler

The optional `ekartoteka-scheduler` service runs the same image as a persistent,
non-root scheduler. It invokes the CLI directly; it neither mounts the Docker
socket nor starts sibling containers. The default schedule is `0 9 * * *` in
`Europe/Warsaw`, leaving time before Ledger's 09:30 daily `system-run`.

Set the schedule and timezone in the deployment `.env` file (not in the
credential file):

```dotenv
OBLIDOG_INTEGRATIONS_VERSION=v0.2.0
EKARTOTEKA_CRON=0 9 * * *
OBLIDOG_SCHEDULER_TIMEZONE=Europe/Warsaw
```

Enable it after pulling the selected immutable image tag:

```bash
docker compose pull ekartoteka-scheduler
docker compose up -d ekartoteka-scheduler
docker compose logs -f ekartoteka-scheduler
```

Disable it with `docker compose stop ekartoteka-scheduler`. Manual runs remain
available through `docker compose run --rm ekartoteka`. The scheduler prevents
overlapping runs with a per-integration `flock` lock and writes start, finish,
duration, outcome, and exit code to Compose logs. A failed run is logged and
does not stop later scheduled runs.

To check whether a run currently holds the lock:

```bash
docker compose exec ekartoteka-scheduler sh -c \
  'flock -n /home/app/.local/state/oblidog-integrations/ekartoteka.lock -c "echo idle" || echo running'
```

## Releases

Releases use Conventional Commits and a reviewable release PR:

- `fix:` and `perf:` prepare a patch release;
- `feat:` prepares a minor release;
- `BREAKING CHANGE:` in the footer or `!` after the type prepares a major release.

Documentation, test, CI, and ordinary chore commits do not create a release.
On a qualifying push to `main`, Commitizen updates `pyproject.toml`, `uv.lock`,
and `CHANGELOG.md` on a `release/vX.Y.Z` branch and creates (or reuses) a
`bump: version X.Y.Z` PR. Merge that PR after CI approval. The finalizer then
creates the annotated tag and GitHub Release and explicitly dispatches the
multi-platform GHCR image publication.

The first release is intentional and manual: run **Bootstrap initial release**
from the Actions tab on `main` with `release_tag=v0.1.0`. It validates the
project version, creates the annotated tag and GitHub Release, then publishes
the initial image. Subsequent releases use the release-PR flow above.

Generate a local changelog or inspect the next version with:

```bash
uv run cz version -p
uv run cz bump --dry-run --yes --get-next
```

For a direct local invocation with credentials, use:

```bash
docker run --rm \
  --env-file demo.env \
  oblidog-integrations:local demo
```
