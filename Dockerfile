# syntax=docker/dockerfile:1

ARG VERSION=0.0.0

FROM ghcr.io/astral-sh/uv:0.11.32 AS uv

FROM python:3.14-slim-trixie AS builder
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

FROM python:3.14-slim-trixie AS runtime
ARG VERSION
LABEL org.opencontainers.image.title="oura-collector" \
      org.opencontainers.image.description="Sync Oura Ring API v2 data into PostgreSQL" \
      org.opencontainers.image.source="https://github.com/kgrubb/oura-helm-chart" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.version="${VERSION}"
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH" \
    HOME=/tmp \
    TMPDIR=/tmp \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
USER 65534:65534
WORKDIR /tmp
ENTRYPOINT ["oura-collector"]
