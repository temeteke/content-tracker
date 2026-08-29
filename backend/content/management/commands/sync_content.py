from django.core.management.base import BaseCommand, CommandError
from django.utils.module_loading import import_string

from content.services import import_candidates


class Command(BaseCommand):
    help = "Pull metadata from one or more source adapters."

    def add_arguments(self, parser):
        parser.add_argument(
            "adapters",
            nargs="+",
            help="Dotted class paths implementing the SourceAdapter protocol.",
        )

    def handle(self, *args, **options):
        total_created = 0
        total_updated = 0

        for adapter_path in options["adapters"]:
            try:
                adapter_class = import_string(adapter_path)
                adapter = adapter_class()
                candidates = adapter.fetch()
                created, updated = import_candidates(candidates)
            except (AttributeError, ImportError, TypeError, ValueError) as exc:
                raise CommandError(f"{adapter_path}: {exc}") from exc

            total_created += created
            total_updated += updated
            self.stdout.write(
                self.style.SUCCESS(
                    f"{adapter_path}: created={created} updated={updated}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"total: created={total_created} updated={total_updated}"
            )
        )
