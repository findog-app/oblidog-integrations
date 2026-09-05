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
tag. Do not deploy until the selected tag appears in [GitHub
Releases](https://github.com/oblidog/oblidog-integrations/releases) and the
release's image-publication workflow has completed.

### Deploy e-Kartoteka on a host

The deployment host needs Docker Engine with the Compose plugin and access to
GHCR. If the package is private, authenticate before pulling with a GitHub
token that has package-read access:

```bash
docker login ghcr.io
```

Choose an existing release tag and clone the matching Compose configuration.
Using the same tag for both prevents a newer configuration from running against
an older image.

```bash
export OBLIDOG_INTEGRATIONS_VERSION=vX.Y.Z # replace with an existing release tag
git clone --branch "$OBLIDOG_INTEGRATIONS_VERSION" --depth 1 \
  https://github.com/oblidog/oblidog-integrations.git
cd oblidog-integrations
cp .env.deploy.example .env
cp .env.ekartoteka.example .env.ekartoteka
chmod 600 .env.ekartoteka
```

Edit `.env` and replace its version with the selected release tag. Edit
`.env.ekartoteka` with `EKARTOTEKA_USERNAME`, `EKARTOTEKA_PASSWORD`,
`OBLIDOG_URL`, `OBLIDOG_API_KEY`, and `OBLIDOG_CATEGORY_CODE`. Keep both files
on the host: they are ignored by Git and excluded from image builds.

Validate the resolved configuration, pull the immutable image, and make one
manual run before enabling the scheduler:

```bash
docker compose config --quiet
docker compose pull
docker compose run --rm ekartoteka
```

If that run succeeds, enable the persistent scheduler and verify it:

```bash
docker compose up -d --no-deps ekartoteka-scheduler
docker compose ps
docker compose logs -f ekartoteka-scheduler
```

Future integrations are additional Compose services using the same image with
their own command and `env_file`.

### Upgrade and rollback

To upgrade, edit `OBLIDOG_INTEGRATIONS_VERSION` in `.env` to another existing
release tag, then pull and recreate only the scheduler. Run the same steps with
an earlier tag to roll back.

```bash
docker compose config --quiet
docker compose pull ekartoteka-scheduler
docker compose up -d --no-deps --force-recreate ekartoteka-scheduler
docker compose ps
```

The scheduler is the only long-lived service. It does not deploy itself or the
Ledger; updating it is an explicit host operation.

### e-Kartoteka scheduler

The optional `ekartoteka-scheduler` service runs the same image as a persistent,
non-root scheduler. It invokes the CLI directly; it neither mounts the Docker
socket nor starts sibling containers. The default schedule is `0 9 * * *` in
`Europe/Warsaw`, leaving time before Ledger's 09:30 daily `system-run`.

Set the schedule and timezone in the deployment `.env` file (not in the
credential file). Start from `.env.deploy.example`:

```dotenv
# Use an existing immutable GitHub Release tag.
OBLIDOG_INTEGRATIONS_VERSION=vX.Y.Z
EKARTOTEKA_CRON=0 9 * * *
OBLIDOG_SCHEDULER_TIMEZONE=Europe/Warsaw
```

Enable it after the manual deployment check:

```bash
docker compose pull ekartoteka-scheduler
docker compose up -d ekartoteka-scheduler
docker compose logs -f ekartoteka-scheduler
```

Disable it with `docker compose stop ekartoteka-scheduler`. Manual runs remain
available through `docker compose run --rm ekartoteka`. Both services mount the
same named state volume and use the same per-integration `flock` lock, so manual
and scheduled runs cannot overlap. The wrapper writes start, finish, duration,
outcome, and exit code to Compose logs. A failed run is logged and does not stop
later scheduled runs.

To check whether a run currently holds the lock:

```bash
docker compose exec ekartoteka-scheduler sh -c \
  'flock -n /home/app/.local/state/oblidog-integrations/ekartoteka.lock -c "echo idle" || echo running'
```

### NJU Mobile accounts

The `nju` integration reads invoices from one NJU Mobile account and uses only
invoices whose portal period matches the current `MM.RRRR`. It sums their full
amounts, updates the one matching current-month Oblidog obligation, and marks
it `ready` when any invoice is unpaid or `paid` when all are settled.

Run every account in a separate container with a separate credential file and
Oblidog category. [`compose.nju.accounts.example.yaml`](compose.nju.accounts.example.yaml)
contains two isolated account pairs (manual + scheduler). Copy it and create a
credential file for each account:

```bash
cp compose.nju.accounts.example.yaml compose.nju.accounts.yaml
cp .env.nju.example .env.nju.account-one
cp .env.nju.example .env.nju.account-two
chmod 600 .env.nju.account-one .env.nju.account-two
```

Set a distinct `NJU_ACCOUNT_NAME` and `OBLIDOG_CATEGORY_CODE` in each file.
Add the schedules to the deployment `.env` file; staggering them is optional
because each account has its own lock volume:

```dotenv
NJU_ACCOUNT_ONE_CRON=0 9 * * *
NJU_ACCOUNT_TWO_CRON=5 9 * * *
```

Validate, pull, and manually test each account before enabling its scheduler:

```bash
docker compose -f compose.nju.accounts.yaml config --quiet
docker compose -f compose.nju.accounts.yaml pull
docker compose -f compose.nju.accounts.yaml run --rm nju-account-one
docker compose -f compose.nju.accounts.yaml run --rm nju-account-two
docker compose -f compose.nju.accounts.yaml up -d \
  nju-account-one-scheduler nju-account-two-scheduler
```

The two schedulers use the same image and `nju` command, but separate `env_file`
and lock volumes. A manual run of an account shares that account's lock; it does
not block the other account.

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
