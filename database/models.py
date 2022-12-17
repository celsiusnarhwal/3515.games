########################################################################################################################
#                         Copyright (C) 2022-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import datetime

from pony.orm import *

db = Database()


class ChessGame(db.Entity):
    id = PrimaryKey(int, auto=True)
    user_id = Required(str)
    white = Required(str)
    black = Required(str)
    server = Required(str)
    result = Required(str)
    date = Required(str)
    date_saved = Required(datetime.datetime, default=datetime.datetime.utcnow())
    pgn = Required(str)
