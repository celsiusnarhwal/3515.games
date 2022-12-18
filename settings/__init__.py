########################################################################################################################
#                         Copyright (C) 2022-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Bot settings.
"""

import os

match os.getenv("DOPPLER_ENVIRONMENT"):
    case "dev":
        from settings.envs.dev import *
    case "prd":
        from settings.envs.prd import *
    case _:
        raise Exception(f"Unkown environment: {os.getenv('DOPPLER_ENVIRONMENT')}")
