# Architecture

## Responsibility

content-tracker owns content metadata, arbitrary hierarchy, consumption planning/status,
consumption history, external-record links, and source-adapter interfaces.

It does not own media files, playback position, source credentials, or deployment configuration.

## Core model

### ContentItem

A ContentItem can represent consumable content or group other ContentItems. The hierarchy is
generic rather than forcing a Title/Series/Episode model.

### ContentLink

A ContentLink maps a ContentItem to a source record or information page. URLs are globally
unique. A source/external-ID pair is also unique when present.

### ConsumptionHistory

Each consumption is a separate record, allowing rewatching, relistening, and rereading.

## Source adapters

Adapters are pull-based and fetch metadata only. They do not download media. Credentials and
endpoint configuration are runtime configuration and must not be committed.

## Deployment boundary

Application containers may be built from this repository. Kubernetes manifests, Helm charts,
Helmfile configuration, ingress, storage, and environment-specific secrets belong in a
separate deployment repository.
