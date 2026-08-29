# ADR 0001: Use URL as the MVP content import identity

Status: Accepted

## Context

A source adapter needs a way to decide whether an imported record already exists.
A more general model could separate:

- a human-usable ContentLink URL
- an ExternalReference containing a source instance and source-specific external ID

That separation is useful when source IDs are more stable than URLs, but it adds models and
synchronization rules before a concrete adapter requires them.

## Decision

For the MVP, ContentLink.url is globally unique and is also the content import identity key.

A ContentCandidate therefore provides a URL but does not provide a source-specific external ID.
When an adapter imports a candidate:

1. content-tracker looks up ContentLink by URL;
2. if found, the associated ContentItem is updated;
3. otherwise, a new ContentItem and ContentLink are created.

Only HTTP(S) URLs are accepted.

## Consequences

The model and adapter API remain small and easy to understand.

A URL change in an external source may make an existing item appear to be a new item. URL
normalization may also become necessary for some sources.

If a real adapter demonstrates that URLs are not stable or sufficient identifiers, introduce
ExternalReference with a source-specific identity at that time rather than pre-emptively.

SourceInstance remains a planned extension for representing configured external sources, but
it is not required for this decision.
