# content-tracker

Content Consumption Manager for tracking planned and completed consumption across media types.

The application is intentionally separated from media storage and playback systems. Source systems remain authoritative for files and playback details; content-tracker imports metadata and manages cross-source organization, planning state, and consumption history.

## Scope

- Track metadata for web video, TV recordings, radio, podcasts, books, manga, and other content.
- Organize ContentItems in an arbitrary parent/child hierarchy.
- Attach globally unique ContentLinks; use URL as the MVP import identity key.
- Plan content with `planned`, `active`, `completed`, and `dropped` states.
- Record multiple consumption events per ContentItem.
- Merge duplicate ContentItems manually while retaining their links and history.
- Import metadata through pull-based adapters.

## Non-goals

content-tracker does **not** own media files, playback position, authentication credentials for source systems, or source-system deployment details. Those remain responsibilities of the source libraries and players.

## Technology

- Backend: Django + Django Ninja
- Database: PostgreSQL
- Frontend: Vue 3 + TypeScript + Vite + Vuetify + Pinia
- Runtime packaging: containers

Kubernetes manifests, Helm charts, and environment-specific deployment configuration are intentionally maintained in a separate deployment repository. This repository contains only application code and application-level configuration.

## Development

The backend can use SQLite when `DB_HOST` is empty, so PostgreSQL is not required for basic local development.

Backend:

```console
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
python manage.py migrate
python manage.py runserver
```

Frontend:

```console
cd frontend
npm install
npm run dev
```

The Vite development server proxies `/api` to the backend. Override `VITE_DEV_PROXY_TARGET` locally if necessary.

### Source synchronization

Source adapters implement `content.adapters.base.SourceAdapter` and return metadata-only `ContentCandidate` objects. Each candidate supplies a globally unique HTTP(S) URL, which is currently used as the import identity key.

Run one or more adapters with:

```console
python manage.py sync_content package.module.AdapterClass
```

A deployment repository can invoke the same command from a Kubernetes CronJob. Adapter endpoints and credentials must be supplied at runtime rather than committed here.

See [ADR 0001](docs/decisions/0001-use-url-as-mvp-identity.md) for the URL identity decision.

## Public repository policy

This repository must not contain private deployment details or secrets. In particular, do not commit:

- credentials, tokens, cookies, or API keys
- private hostnames, internal domains, or private IP addresses
- personal source URLs or local filesystem paths
- production database connection strings
- exported user consumption data

Runtime-specific configuration belongs in environment variables or deployment-specific secret/configuration stores.

## Development status

Initial MVP development is in progress.
