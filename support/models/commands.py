########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import discord


class SlashCommandGroup(discord.SlashCommandGroup):
    """
    Equivalent to :class:`discord.SlashCommandGroup` with the exception that commands created by instances of this class
    are always guild-only.

    Notes
    -----
    All of 3515.games' comnmands are guild-only. Using this subclass is preferred to explicitly passing
    `guild_only=True` to every instantiation of :class:`discord.SlashCommandGroup`.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, guild_only=True)


class Pseudocommand(discord.commands.SlashCommand):
    """
    A pseudocommand.

    Notes
    -----
    Pseudocommands are corountines that are treated like commands at the code level but are not actually accessible
    to end users. 3515.games uses a custom subclass of :class:`discord.bot.Bot` that blocks the registration
    of pseudocommands with the Discord API.

    Unlike regular commands, pseudocommands can be called directly without losing their checks.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, guild_only=True)

    async def __call__(self, ctx, *args, **kwargs):
        if await self.can_run(ctx):
            return await super().__call__(ctx, *args, **kwargs)
