from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from content.source_config import SourceConfigError, load_sources_file
from content.sync import sync_source


class Command(BaseCommand):
    help = "Synchronize configured sources through installed adapter plugins."

    def add_arguments(self, parser):
        parser.add_argument(
            "sources",
            nargs="*",
            help="Source keys to synchronize. Omit to synchronize all enabled sources.",
        )
        parser.add_argument(
            "--sources-file",
            help="Path to sources.yaml. Overrides CONTENT_TRACKER_SOURCES_FILE.",
        )

    def handle(self, *args, **options):
        configured_path = options["sources_file"] or settings.CONTENT_TRACKER_SOURCES_FILE
        if not configured_path:
            raise CommandError(
                "sources file is not configured; use --sources-file or "
                "CONTENT_TRACKER_SOURCES_FILE"
            )

        try:
            document = load_sources_file(Path(configured_path))
        except SourceConfigError as exc:
            raise CommandError(str(exc)) from exc

        by_key = {source.key: source for source in document.sources}
        requested = options["sources"]

        if requested:
            unknown = [key for key in requested if key not in by_key]
            if unknown:
                raise CommandError(f"unknown source keys: {', '.join(unknown)}")
            selected = [by_key[key] for key in requested]
        else:
            selected = [source for source in document.sources if source.enabled]

        failures: list[str] = []
        total_created = 0
        total_updated = 0

        for source in selected:
            if not source.enabled:
                failures.append(f"{source.key}: source is disabled")
                continue

            try:
                outcome = sync_source(source)
            except Exception as exc:
                failures.append(f"{source.key}: {type(exc).__name__}: {exc}")
                self.stderr.write(self.style.ERROR(failures[-1]))
                continue

            total_created += outcome.created
            total_updated += outcome.updated
            self.stdout.write(
                self.style.SUCCESS(
                    f"{source.key}: created={outcome.created} updated={outcome.updated}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"total: created={total_created} updated={total_updated}"
            )
        )

        if failures:
            raise CommandError(f"{len(failures)} source(s) failed")
