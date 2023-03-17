########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

from functools import partial

import discord

SlashCommandGroup = partial(discord.SlashCommandGroup, guild_only=True)


class Pseudocommand(discord.SlashCommand):
    """
    A pseudocommand.

    Pseudocommands are corountines that are treated like commands at the code level but are not registered with
    Discord and thus not accessible to end users.

    Notes
    -----
    Unlike regular commands, pseudocommands can be called directly without losing their checks.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, guild_only=True)

    async def __call__(self, ctx, *args, **kwargs):
        if await self.can_run(ctx):
            return await super().__call__(ctx, *args, **kwargs)
