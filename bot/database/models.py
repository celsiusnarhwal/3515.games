########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from datetime import datetime

import discord
from pony.orm import *

db = Database()


class ChessGame(db.Entity):
    id = PrimaryKey(int, auto=True)
    user_id = Required(str)
    white = Required(str)
    white_id = Required(str)
    black = Required(str)
    black_id = Required(str)
    server = Required(str)
    result = Required(str)
    date = Required(datetime)
    date_saved = Required(datetime, default=datetime.utcnow())
    pgn = Required(str)

    @classmethod
    def get_user_games(cls, user: discord.User):
        return cls.select(lambda g: g.user_id == str(user.id)).order_by(
            lambda g: desc(g.date_saved)
        )
