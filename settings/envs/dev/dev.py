########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Development settings.
"""

from settings.base import Settings

settings = Settings(
    bot_name="3515.games.dev",
    app_id=960228863986761778,
    database={
        "provider": "sqlite",
        "filename": "db.sqlite3",
        "create_db": True,
    },
)
