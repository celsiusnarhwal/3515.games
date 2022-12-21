########################################################################################################################
#                         Copyright (C) 2022-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Bot settings.
"""

import os as _os

settings = None

_configuration = _os.getenv("DOPPLER_CONFIG")
_module = f"settings.configs.{_configuration}"

try:
    exec(f"from {_module} import settings")
except ImportError:
    raise Exception(f"Unknown configuration: {_configuration}")
