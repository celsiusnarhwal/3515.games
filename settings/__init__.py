########################################################################################################################
#                         Copyright (C) 2022-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

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
