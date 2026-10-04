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

This MVP also has no API authentication: it is intended for single-user local use behind
localhost or a trusted reverse proxy. Do not expose it directly to untrusted networks.

## Technology

- Backend: Django + Django Ninja
- Database: PostgreSQL
- Frontend: Vue 3 + TypeScript + Vite + Vuetify + Pinia
- Runtime packaging: containers

Kubernetes manifests, Helm charts, plugin composition, and environment-specific deployment configuration are intentionally maintained in a separate deployment repository.

## Development

The backend loads the repository-root `.env` file at startup. It uses SQLite while `DB_HOST` is
empty and PostgreSQL when `DB_HOST` is set. With `DJANGO_DEBUG=true` a development secret is used
when `DJANGO_SECRET_KEY` is unset; when `DJANGO_DEBUG` is false, `DJANGO_SECRET_KEY` must be set or
startup fails.

### VS Code Dev Container (recommended)

The repository includes a Dev Container for VS Code. Open the repository folder and run
`Dev Containers: Reopen in Container`. The first start creates `.env` from `.env.example` if
it is missing.

The Dev Container is defined with Docker Compose and starts these services:

- `workspace`: the VS Code container (Python 3.14 and Node.js 24) where you edit and run tests.
- `db`: PostgreSQL 17, shared with the production-equivalent stack below.
- `backend` / `frontend`: the application in development mode with the source bind-mounted
  (`runserver` and the Vite dev server).

Ports 8000 and 5173 are forwarded automatically. This setup requires Docker Compose v2.24.4 or
later (for the `!override` tag used to remap the frontend port).

### Running without the Dev Container

The backend can use SQLite when `DB_HOST` is empty, so PostgreSQL is not required for basic
local development.

Backend:

```console
cp .env.example .env
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
npm ci
npm run dev
```

The Vite development server reads the repository-root `.env` and proxies `/api` to the
backend. Override `VITE_DEV_PROXY_TARGET` locally if necessary.

Frontend checks:

```console
cd frontend
npm run lint
npm run format:check
npm run typecheck
npm run test
npm run test:e2e
```

The E2E smoke test expects the backend on `E2E_API_URL` (default
`http://localhost:8000/api`) and the Vite dev server on `E2E_BASE_URL` (default
`http://localhost:5173`), and it cleans up the content it creates.

## API

Interactive API docs (development): `http://localhost:8000/api/docs`.

- `GET /api/health` checks database connectivity and returns `503` when unavailable.
- `GET /api/items` returns `X-Total-Count` with the number of matching items and
  supports `content_type`, `status`, `query`, `parent_id`, `limit`, and `offset`.
- `DELETE /api/items/{id}?revision=N` deletes an item with optimistic locking; its
  children are detached, and its links and history are removed.
- `PATCH /history/{id}` and `DELETE /history/{id}` correct or remove a consumption
  record and bump the parent item revision.
- `POST /api/items/{id}/merge` merges another item into the target.

### Production-equivalent stack

The root `compose.yaml` builds the production images (gunicorn + nginx) and uses the same
PostgreSQL data volume as the Dev Container, so you can verify behavior against the data you
created during development. It is a reference stack, not the production deployment; Kubernetes
manifests live in the separate deployment repository.

```console
cp .env.example .env
make up
```

The frontend is served through Traefik at `http://content-tracker.localhost`. To use
a distinct local hostname namespace, set `TRAEFIK_HOST_SUFFIX=dev.localhost` in
`.env`; the URL then becomes `http://content-tracker.dev.localhost`. The database
is not published to the host.

The Makefile uses `compose.yaml` together with `compose.traefik.yaml` and creates the
external `traefik` Docker network if it does not already exist. The Traefik instance
itself must also be attached to that network. Apply migrations with:

```console
docker compose run --rm backend python manage.py migrate
```

Development and verification use the same service names, so run one mode at a time. Stop the
Traefik-backed stack with `make down`. Reset the shared database with
`docker compose -f compose.yaml -f compose.traefik.yaml down -v`.

Back up the PostgreSQL volume before destructive operations. The deployment repository owns
automated backups; for a manual snapshot:

```console
docker compose exec db pg_dump -U content_tracker content_tracker > backup.sql
```

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
command line. From the `backend` directory, the example file is one level up:

```console
python manage.py sync_content --sources-file ../sources.example.yaml
```

The example references a `podcast` adapter that is not part of this repository. A reference
implementation is maintained separately and installed by the deployment image build.
Otherwise `sync_content` reports that the adapter is not installed.

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

MVP scope (hierarchy, URL-identity links, four planning states, multiple consumption
records, manual merge, adapter import via CLI) is implemented across the API and UI.
Remaining work is driven by real-adapter feedback and deployment needs.
