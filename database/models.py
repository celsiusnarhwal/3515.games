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
