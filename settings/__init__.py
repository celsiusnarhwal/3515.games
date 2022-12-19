########################################################################################################################
#                         Copyright (C) 2022-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Bot settings.
"""

import inspect as _inspect
import os as _os
import sys as _sys

from settings.base import *  # ensure editor code completion only cares about settings.base

def _is_setting(name: str) -> bool:
    return name.isupper() and not name.startswith("_")

configuration = _os.getenv("DOPPLER_ENVIRONMENT")
module = f"settings.envs.{configuration}"

try:
    exec(f"from {module} import *")
except ImportError:
    raise Exception(f"Unknown configuration: {configuration}")

defined = {x: y for x, y in _inspect.getmembers(_sys.modules[module]) if _is_setting(x)}
required = [x for x, _ in _inspect.getmembers(_sys.modules["settings.base"]) if _is_setting(x)]

match set(defined.keys()).difference(required):
    case _unknown if _unknown:
        raise Exception(f"Unknown settings: {' '.join(_unknown)}")

match [name for name in required if defined.get(name) is None]:
    case _undefined if _undefined:
        raise Exception(f"Undefined settings: {' '.join(_undefined)}")
