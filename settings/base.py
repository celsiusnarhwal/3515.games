########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
The base settings configuration.
"""
import typing as T

import discord
from pydantic import BaseSettings, Field, StrictInt, StrictStr


class Settings(BaseSettings):
    """
    Represents a settings configuration. New settings configurations should be created with Kurisu
    (``kurisu settings new``).

    Settings configurations must respect this class' type annotations and define values for any fields that lack
    defaults. 3515.games will refuse to start if either of these conditions are not met.

    Parameters
    ----------
    bot_name : str
        The name of 3515.games' bot user.
    app_id : int
    database : dict
        A dictionary of options for 3515.games' database connection. For supported options, see Pony's documentation:
        https://docs.ponyorm.org/database.html#binding-the-database-object-to-a-specific-database
        3515.games' application ID.
    owner_id : int, optional, default: 170966436125212673
        The user ID of 3515.games' owner. The default corresponds to celsiusnarhwal#3515.
    intents : discord.Intents, optional, default: discord.Intents.default() + discord.Intents.members
        Gateway Intents. By default, this includes all non-privileged intents plus the GUILD_MEMBERS intent.
        (See: https://discord.com/developers/docs/topics/gateway#gateway-intents)
    debug_guilds: list[int], optional, default: []
        A list of IDs of guilds where 3515.games should create commands exclusively. If this list is non-empty,
        3515.games will only be usable in the specified guilds.
    extensions : list[str], optional, default: []
        A list of extensions to load on startup.
    disabled_cogs : list[discord.Cog], optional, default: []
        A list of cogs to block from initialization. Commands and listeners and these cogs will not be registered on
        startup and will thus not be usable.
    nltk_corpora : list[str], optional, default: ["averaged_perceptron_tagger"]
        A list of NLTK corpora to download on startup. (See: https://www.nltk.org/book/ch02)
    token : str, optional, default: os.getenv("BOT_TOKEN")
        3515.games' bot token.
    suppressed_warnings: list[Warning], optional, default: [RuntimeWarning]
        A list of warnings to suppress. (See: https://docs.python.org/3/library/warnings.html#warning-filter)
    """

    # Required
    bot_name: StrictStr
    app_id: StrictInt
    database: dict

    # Optional
    owner_id: StrictInt = 170966436125212673
    intents: discord.Intents = discord.Intents.default() + discord.Intents.members
    debug_guilds: list[StrictInt] = []
    extensions: list[StrictStr] = []
    disabled_cogs: list[discord.Cog] = []
    nltk_corpora: list[StrictStr] = ["averaged_perceptron_tagger"]
    token: StrictStr = Field(..., env="BOT_TOKEN")
    suppressed_warnings: list[T.Type[Warning]] = [RuntimeWarning]
