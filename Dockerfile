# The API in one container. Postgres, Langfuse and the rest were cut for v1,
# so the whole app is this one image plus a folder for checks.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv

# Run as a normal user. The Agent SDK's runtime also needs a writable home folder.
RUN useradd --create-home app
WORKDIR /app
RUN chown app /app
USER app

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/home/app/venv

# Dependencies first, so editing code doesn't reinstall them.
COPY --chown=app pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-dev --no-install-project

COPY --chown=app . .
RUN uv sync --locked --no-dev

ENV PATH="/home/app/venv/bin:$PATH" EUDR_CHECKS_DIR=/app/checks
EXPOSE 8000
CMD ["uvicorn", "eudr.gateway.app:app", "--host", "0.0.0.0", "--port", "8000"]
