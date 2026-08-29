# content-tracker

Content Consumption Manager for tracking planned and completed consumption across media types.

The application is intentionally separated from media storage and playback systems. Source systems remain authoritative for files and playback details; content-tracker imports metadata and manages cross-source organization, planning state, and consumption history.

## Scope

- Track metadata for web video, TV recordings, radio, podcasts, books, manga, and other content.
- Organize ContentItems in an arbitrary parent/child hierarchy.
- Attach globally unique ContentLinks and preserve source metadata for later processing.
- Plan content with `planned`, `active`, `completed`, and `dropped` states.
- Record multiple consumption events per ContentItem.
- Merge duplicate ContentItems manually while retaining their links.
- Import metadata through pull-based adapters.

## Non-goals

content-tracker does **not** own media files, playback URLs, authentication credentials for source systems, or playback position. Those remain responsibilities of the source libraries and players.

## Technology

- Backend: Django + Django Ninja
- Database: PostgreSQL
- Frontend: Vue 3 + TypeScript + Vite + Vuetify + Pinia
- Runtime packaging: containers

Kubernetes manifests, Helm charts, and environment-specific deployment configuration are intentionally maintained in a separate deployment repository. This repository contains only application code and application-level configuration.

## Public repository policy

This repository must not contain private deployment details or secrets. In particular, do not commit:

- credentials, tokens, cookies, or API keys
- private hostnames, internal domains, or private IP addresses
- personal source URLs or local filesystem paths
- production database connection strings
- exported user consumption data

Runtime-specific configuration belongs in environment variables or deployment-specific secret/configuration stores.

## Development status

Initial implementation is in progress.
