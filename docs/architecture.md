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
