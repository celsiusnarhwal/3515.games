########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Bot settings.
"""
import importlib
import os

from path import Path

from settings.base import Settings

__all__ = ["settings"]

if (
    env_dir := (
        Path(__file__).parent / "envs" / (env := os.getenv("DOPPLER_ENVIRONMENT"))
    )
).exists():
    if (env_dir / (cfg := os.getenv("DOPPLER_CONFIG"))).with_suffix(".py").exists():
        try:
            settings: Settings = importlib.import_module(
                f"settings.envs.{env}.{cfg}"
            ).settings
        except ImportError:
            raise ImportError(
                f"Couldn't import settings from {env}/{cfg}.py. "
                f"Are you sure {env} is a Python package?"
            )
    else:
        raise Exception(f"No settings configuration for {env}/{cfg}")
else:
    raise Exception(f"Unknown environment: {env}")
