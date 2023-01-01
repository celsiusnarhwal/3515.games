########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Bot settings.
"""
import os as _os

from path import Path as _Path

from settings.base import Settings as _Settings

settings: _Settings = None

_configs_dir = _Path(__file__).parent / "envs"

match _os.getenv("DOPPLER_ENVIRONMENT"):
    case _environment_dir if (_configs_dir / _environment_dir).exists():
        match _os.getenv("DOPPLER_CONFIG"):
            case _config_file if (
                _configs_dir / _environment_dir / _config_file
            ).with_suffix(".py").exists():
                try:
                    exec(
                        f"from settings.envs.{_environment_dir}.{_config_file} import settings"
                    )
                except ImportError:
                    raise ImportError(
                        f"Couldn't import settings from {_environment_dir}/{_config_file}.py. "
                        f"Are you sure {_environment_dir} is a Python package?"
                    )
            case _ as _config:
                raise Exception(
                    f"No settings configuration for {_environment_dir}/{_config}"
                )
    case _ as _environment:
        raise Exception(f"Unknown environment: {_environment}")
