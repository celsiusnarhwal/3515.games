########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Bot settings.
"""
import importlib as _importlib
import os as _os

from path import Path as _Path

from settings.base import Settings as _Settings

# why is this allowed
if (
    _env_dir := (
        _Path(__file__).parent / "envs" / (_env := _os.getenv("DOPPLER_ENVIRONMENT"))
    )
).exists():
    if (_env_dir / (_cfg := _os.getenv("DOPPLER_CONFIG"))).with_suffix(".py").exists():
        try:
            settings: _Settings = _importlib.import_module(
                f"settings.envs.{_env}.{_cfg}"
            ).settings
        except ImportError:
            raise ImportError(
                f"Couldn't import settings from {_env}/{_cfg}.py. "
                f"Are you sure {_env} is a Python package?"
            )
    else:
        raise Exception(f"No settings configuration for {_env}/{_cfg}")
else:
    raise Exception(f"Unknown environment: {_env}")
