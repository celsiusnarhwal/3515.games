"""
The settings package enables 3515.games to dynamically load a particular settings configuration based on the
environment it's running in.
"""

from settings.base import *

_environments = {
    "dev": "settings.envs.dev",
    "prd": "settings.envs.prod",
}

_current_environment = os.getenv("DOPPLER_ENVIRONMENT")
configuration = _environments.get(_current_environment)

if configuration:
    exec(f"from {configuration} import *")
else:
    raise Exception(f"Unknown environment: {_current_environment}")
