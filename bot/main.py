########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
The program entrypoint.
"""
import logging
import warnings

import clockworks
import nest_asyncio as nest
import nltk
from click import secho as print
from database.models import db
from path import Path
from settings import settings

from bot import bot


def check_current_directory():
    if Path.getcwd() != Path(__file__).parent:
        raise RuntimeError("The current working directory must be /bot.")


def configure_logging():
    logger = logging.getLogger("discord")
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(
        filename=f"../3515.games.log", encoding="utf-8", mode="w"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
    )
    logger.addHandler(handler)


def suppress_warnings():
    for warning in settings.suppressed_warnings:
        warnings.filterwarnings("ignore", category=warning)


def configure_nltk():
    for corpus in settings.nltk_corpora:
        nltk.download(corpus, quiet=True)


def configure_database():
    db.bind(**settings.database)
    db.generate_mapping(create_tables=True)


def load_extensions():
    bot.load_extensions(*settings.extensions)


def setup():
    check_current_directory()
    configure_logging()
    suppress_warnings()
    configure_nltk()
    configure_database()
    load_extensions()


if __name__ == "__main__":
    print(f"\n{open('../COPYING').read()}\n", fg="magenta")

    print(f"Hello! {settings.bot_name} will be ready in just a moment.")
    setup()

    nest.apply()
    clockworks.start_clock()
    bot.run(settings.token)
