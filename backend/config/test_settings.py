import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key")
os.environ.setdefault("DJANGO_DEBUG", "false")

from .settings import *  # noqa: E402,F401,F403
