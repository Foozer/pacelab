FROM python:3.12-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

ARG UID=1000
ARG GID=1000

RUN groupadd --gid ${GID} pacelab \
    && useradd --uid ${UID} --gid pacelab --create-home --shell /usr/sbin/nologin pacelab

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts

RUN chmod +x /app/scripts/entrypoint.sh \
    && pip install --no-cache-dir -e . \
    && chown -R pacelab:pacelab /app

ENTRYPOINT ["/app/scripts/entrypoint.sh"]


FROM base AS development

RUN pip install --no-cache-dir -e ".[dev]" \
    && chown -R pacelab:pacelab /app

USER pacelab

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--proxy-headers"]


FROM base AS production

USER pacelab

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
