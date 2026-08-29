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
- Import metadata through separately installed source-adapter plugins.

## Non-goals

content-tracker does **not** own media files, playback position, authentication credentials for source systems, plugin installation, or source-system deployment details. Those remain responsibilities of source systems and deployment configuration.

## Technology

- Backend: Django + Django Ninja
- Database: PostgreSQL
- Frontend: Vue 3 + TypeScript + Vite + Vuetify + Pinia
- Runtime packaging: containers

Kubernetes manifests, Helm charts, plugin composition, and environment-specific deployment configuration are intentionally maintained in a separate deployment repository.

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

## Source adapters and configuration

Adapters are installed as Python packages and register an entry point in the
`content_tracker.adapters` group. The application discovers only what is already installed in
the runtime image.

List installed adapters:

```console
python manage.py list_adapters
```

Runtime source definitions live in a separate YAML file. content-tracker does not fix its
repository location or mount path. Set `CONTENT_TRACKER_SOURCES_FILE`, or override it on the
command line:

```console
python manage.py sync_content --sources-file ./sources.example.yaml
```

A source definition contains a stable key, an adapter key, and adapter-specific configuration.
The adapter validates its own config with a Pydantic schema. Runtime synchronization state is
stored in the database rather than written back to YAML.

The deployment repository is responsible for a separate plugin manifest such as
`plugins.yaml` and for building an immutable runtime image containing those packages.
content-tracker itself does not install packages at startup.

See:

- [ADR 0001](docs/decisions/0001-use-url-as-mvp-identity.md) for URL identity.
- [ADR 0002](docs/decisions/0002-plugin-and-source-configuration.md) for plugin discovery and source configuration.

## Public repository policy

This repository must not contain private deployment details or secrets. In particular, do not commit:

- credentials, tokens, cookies, or API keys
- private hostnames, internal domains, or private IP addresses
- personal source URLs or local filesystem paths
- production database connection strings
- exported user consumption data

Runtime-specific configuration belongs in environment variables, mounted configuration, or deployment-specific secret stores.

## Development status

Initial MVP development is in progress.
