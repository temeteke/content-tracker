from django.core.management.base import BaseCommand

from content.adapters.registry import discover_adapters


class Command(BaseCommand):
    help = "List installed content-tracker source adapter plugins."

    def handle(self, *args, **options):
        adapters = discover_adapters()
        if not adapters:
            self.stdout.write("No adapters installed.")
            return

        for adapter_key in sorted(adapters):
            self.stdout.write(adapter_key)
