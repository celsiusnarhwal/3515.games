########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import discord
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """
    A settings configuration.

    Parameters
    ----------
    bot_name : str
        The name of 3515.games' bot user.
    app_id : int
        3515.games' application ID.
    database : dict
        Options for 3515.games' database connection. See Pony's documentation[1]_ for supported options.
    intents : discord.Intents, optional, default: discord.Intents.default() + discord.Intents.members
        Gateway Intents[2]_. By default, this includes all non-privileged intents plus the GUILD_MEMBERS intent.
    debug_guilds: list[int], optional, default: []
        IDs of guilds where 3515.games should create commands exclusively. If this list is non-empty, 3515.games will
        only be usable in the specified guilds.
    extensions : list[str], optional, default: []
        Extensions to load on startup.
    disabled_cogs : list[discord.Cog], optional, default: []
        Cogs to *not* register on startup.
    nltk_corpora : list[str], optional, default: ["averaged_perceptron_tagger"]
        NLTK corpora[3]_ to download on startup.
    token : str, optional, default: BOT_TOKEN environment variable
        3515.games' bot token.
    suppressed_warnings: list[Warning], optional, default: [RuntimeWarning]
        Warnings to suppress[4]_.

    References
    ----------
    .. [1] https://docs.ponyorm.org/database.html#binding-the-database-object-to-a-specific-database
    .. [2] https://discord.com/developers/docs/topics/gateway#gateway-intents
    .. [3] https://www.nltk.org/book/ch02
    .. [4] https://docs.python.org/3/library/warnings.html#warning-filter
    """

    # Required
    bot_name: str
    database: dict

    # Optional
    app_id: int = Field(..., env="BOT_APP_ID")
    intents: discord.Intents = discord.Intents.default() + discord.Intents.members
    debug_guilds: list[int] = []
    extensions: list[str] = []
    disabled_cogs: list[discord.Cog] = []
    nltk_corpora: list[str] = ["averaged_perceptron_tagger"]
    token: str = Field(..., env="BOT_TOKEN")
    suppressed_warnings: list[type[Warning]] = [RuntimeWarning]
