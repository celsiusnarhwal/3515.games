"""
The settings package enables 3515.games to dynamically load a particular settings configuration based on the
environment it's running in.
"""
from settings.base import *

_environments = {
    "prd": "settings.envs.prod",
    "dev": "settings.envs.dev",
}

_current_environment = os.getenv("DOPPLER_ENVIRONMENT")

if _current_environment in _environments.keys():
    exec(f"from {_environments[_current_environment]} import *")
else:
    raise Exception(f"Unknown environment: {_current_environment}")
