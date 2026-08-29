# ADR 0002: Discover plugins with entry points and configure sources with YAML

Status: Accepted

## Context

Adapter packages are installed by the deployment image build, while source-specific runtime
configuration must remain outside the public application and plugin repositories.

The deployment repository also needs freedom to choose file names and mount locations.

## Decision

Adapter packages register Python entry points in the `content_tracker.adapters` group.

content-tracker discovers installed adapters through `importlib.metadata`. Adapter packages
implement plugin API v1 from the host-provided `content_tracker_plugin_api` package and must
not access the Django ORM.

Source configuration is supplied in a separate YAML file. The application does not prescribe
its repository location or runtime mount path. The path is supplied by
`CONTENT_TRACKER_SOURCES_FILE` or the `--sources-file` command option.

The YAML file contains desired configuration:

- a stable source `key`
- an adapter entry-point key
- an enabled flag
- plugin-specific `config`

Runtime synchronization state is stored separately in PostgreSQL in `SourceState`, keyed by
the source key.

Plugin installation configuration such as `plugins.yaml` is a deployment concern and is not
read by the running content-tracker application.

## Consequences

The public application repository does not need environment-specific source URLs.

Deployment can freely decide where `sources.yaml` lives and can build an immutable image with
the desired adapter packages.

Removing a source from YAML does not automatically delete its historical SourceState. State
cleanup can be added later if needed.
