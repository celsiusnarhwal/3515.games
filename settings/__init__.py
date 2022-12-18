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

match _os.getenv("DOPPLER_ENVIRONMENT"):
    case "dev":
        from settings.envs.dev import *
    case "prd":
        from settings.envs.prd import *
    case _ as _environment:
        raise Exception(f"Unkown environment: {_environment}")

_undefined = _inspect.getmembers(_sys.modules[__name__], lambda x: x is None)

if _undefined:
    raise Exception(f"Undefined settings: {' '.join([x for x, *_ in _undefined])}")
