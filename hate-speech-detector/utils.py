import os

from django.conf import settings
import environ


def get_env(var_name: str) -> str:
    env = environ.Env()
    environ.Env.read_env(os.path.join(settings.BASE_DIR, ".env"))
    return env(var_name)
