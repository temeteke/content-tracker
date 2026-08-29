# Architecture

## Responsibility

content-tracker owns content metadata, arbitrary hierarchy, consumption planning/status,
consumption history, human-usable content links, and source-adapter interfaces.

It does not own media files, playback position, source credentials, or deployment configuration.

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

## Source adapters

Adapters are pull-based and fetch metadata only. They do not download media. Each
ContentCandidate must provide a valid HTTP(S) URL, which is used as the MVP import identity.

Credentials and endpoint configuration are runtime configuration and must not be committed.

The current adapter interface is intentionally minimal. SourceInstance and richer plugin
configuration will be introduced when the first real external adapter is implemented.

## Deployment boundary

Application containers may be built from this repository. Kubernetes manifests, Helm charts,
Helmfile configuration, ingress, storage, and environment-specific secrets belong in a
separate deployment repository.
