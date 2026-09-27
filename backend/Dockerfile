FROM python:3.14-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml ./
COPY config ./config
COPY content ./content
COPY content_tracker_plugin_api ./content_tracker_plugin_api
COPY manage.py ./


FROM base AS dev

RUN pip install --no-cache-dir -e ".[dev]"

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


FROM base AS prod

RUN pip install --no-cache-dir ".[prod]" \
    && useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--access-logfile", "-"]
