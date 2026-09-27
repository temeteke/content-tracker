# Architecture

## Responsibility

content-tracker owns content metadata, arbitrary hierarchy, consumption planning/status,
consumption history, human-usable content links, source configuration loading, adapter
discovery, and synchronization runtime state.

It does not own media files, playback position, source credentials, plugin installation, or
deployment configuration.

## Core model

### ContentItem

A ContentItem can represent consumable content or group other ContentItems. The hierarchy is
generic rather than forcing a Title/Series/Episode model.

### ContentLink

A ContentLink is a human-usable HTTP(S) URL associated with a ContentItem. URLs are globally
unique.

For the MVP, the URL is also the synchronization identity key. Importing the same URL updates
the existing ContentItem rather than creating a duplicate. Source-specific external IDs are
deliberately not modeled yet.

This keeps the model simple. If a real adapter needs identity that survives URL changes or has
no stable URL, an ExternalReference model can be introduced at that point.

### ConsumptionHistory

Each consumption is a separate record, allowing rewatching, relistening, and rereading.

### SourceDefinition and SourceState

SourceDefinition is read from the runtime YAML file and is the desired configuration. It
contains a stable key, adapter key, enabled flag, and plugin-specific configuration.

SourceState is persisted in PostgreSQL and stores only runtime state such as the adapter sync
cursor, last synchronization time, and last error.

Configuration and runtime state are intentionally separate.

## Concurrency

`ContentItem` and `SourceState` carry a monotonically increasing `revision` integer. Updates use
an optimistic-lock compare-and-set: the caller supplies the revision it read, and the write is a
conditional `UPDATE ... WHERE id = ? AND revision = ?`. A zero-row result means another writer
won the race.

- Source synchronization fetches data outside a transaction, validates the result, then updates
  `SourceState` and imports candidates in a single short transaction. If the revision changed
  during the fetch, the whole result is discarded and reported as a conflict; the cursor never
  moves backwards.
- The `PATCH /api/items/{id}` endpoint requires the expected `revision`. A stale value returns
  `409 Conflict`, and a missing item returns `404 Not Found`.
- Plugin output is validated at the boundary. Candidate titles, URLs, content types, durations,
  timestamps, and metadata must satisfy the same limits as the database, and `next_state` must be
  JSON serializable before any content is imported.
- URL uniqueness is the final guard for concurrent imports. A unique-constraint violation is
  caught per candidate, and the existing link is re-fetched and updated instead of failing the
  whole synchronization.

Concurrency guarantees are defined and tested against PostgreSQL. SQLite is supported only as a
convenience for fast local tests; `SELECT ... FOR UPDATE` is a no-op there, so SQLite is not a
correctness reference.

## Error reporting

Operational errors are reported as structured, value-free summaries so that secrets can never
leak into logs by construction. Only exception class names, Pydantic field paths, and error
codes are recorded; free-text messages and input values from adapter code are never emitted.
Host-authored messages (audited to be value-free) are preserved for diagnostics.

- `SourceState.last_error` and the `sync_content` command output carry these summaries.
- Per-source CLI lines are always type-only summaries; host detail beyond the type lives in
  `last_error` (inspectable via the Django shell, as it is not exposed by the API).
- Detailed tracebacks only appear on explicit `--traceback` debugging runs and unexpected bugs.
  Treat that output as sensitive because traceback frames contain configuration values.

## Local containers

Two Docker Compose configurations exist for local use, and both share one PostgreSQL service and
data volume so that verification sees development data.

- The root `compose.yaml` builds the production-equivalent images (`gunicorn` for the backend,
  `nginx` for the frontend) and is used for verification from the host. It is a reference stack,
  not the production deployment.
- `.devcontainer/compose.yaml` overrides `backend` and `frontend` to build the `dev` stage and
  bind-mount the source, and adds a `workspace` service that VS Code attaches to.

Both compose files use the same service names, so development and verification are run one mode
at a time.

## Plugin API

Adapter packages are normal Python distributions installed into the runtime image. They
register an entry point in the `content_tracker.adapters` group.

The public plugin API lives in `content_tracker_plugin_api`. An adapter declares:

- `api_version`
- a Pydantic `config_model`
- `fetch(SyncContext) -> SyncResult`

Adapters return metadata-only ContentCandidate values. They do not download media and do not
access the content-tracker database.

The host validates each source config with the adapter's Pydantic model before calling it.

## Source configuration

The application accepts the source YAML path through `CONTENT_TRACKER_SOURCES_FILE` or the
`--sources-file` command option. The repository location and Kubernetes mount path are
deployment concerns.

A safe example is available at `sources.example.yaml`.

## Deployment boundary

The deployment repository decides which plugin packages are installed in the immutable runtime
image. A separate deployment-level plugin manifest such as `plugins.yaml` may be used by the
image build, but the running content-tracker application does not read it.

Kubernetes manifests, Helm charts, Helmfile configuration, ingress, storage, image composition,
source file placement, and environment-specific secrets belong in a separate deployment
repository.
