########################################################################################################################
#                         Copyright (C) 2022-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Production settings.
"""
import os

from settings.base import Settings

settings = Settings(
    bot_name="3515.games",
    app_id=939972078323519488,
    database={
        "provider": "postgres",
        "dsn": os.getenv("DATABASE_URL"),
    }
)
