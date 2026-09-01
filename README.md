# oblidog-integrations

Batch and one-shot integrations for Oblidog.

The repository is a monorepo for integrations that run periodically, fetch data from an external provider, synchronize it through `findog-client-python`, and exit. Long-running services such as mail ingestion should live separately.

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

A single image contains all batch integrations. The integration name is passed as the container argument:

```bash
docker build -t oblidog-integrations .

docker run --rm \
  --env-file demo.env \
  oblidog-integrations demo
```

This allows independent systemd timers on the runtime host to invoke different integrations while deployment and dependencies remain centralized.
