FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

# The Oblidog client is temporarily installed from Git until it is published.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.12-slim-bookworm AS runtime

ARG TARGETARCH
ARG SUPERCRONIC_VERSION=v0.2.49

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl tzdata util-linux \
    && case "$TARGETARCH" in \
        amd64) supercronic_arch=amd64; supercronic_sha256=a53ae236602c7338aba3fbaff40bda6300eae3b9fedb8261eb06cfe3724430c1 ;; \
        arm64) supercronic_arch=arm64; supercronic_sha256=02aa0cb229ba09050cba6638059dadb9eedc2276632ea43d6a57a2f8c1629dd5 ;; \
        *) echo "Unsupported supercronic architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac \
    && curl --fail --location --silent --show-error \
        "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${supercronic_arch}" \
        --output /usr/local/bin/supercronic \
    && echo "${supercronic_sha256}  /usr/local/bin/supercronic" | sha256sum --check \
    && chmod 0755 /usr/local/bin/supercronic \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --create-home --shell /usr/sbin/nologin app \
    && install --directory --owner=app --group=app /home/app/.local/state/oblidog-integrations \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY scripts/oblidog-scheduled-run scripts/oblidog-scheduler /usr/local/bin/
RUN chmod 0755 /usr/local/bin/oblidog-scheduled-run /usr/local/bin/oblidog-scheduler

ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1

USER app
ENTRYPOINT ["oblidog-integrations"]
