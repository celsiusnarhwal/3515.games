########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import discord
from discord.ext import commands

import support
import support.views
from cogs import uno


def verify_context(level: str, verify_host: bool = False):
    """
    A decorator which implements a context verification system for UNO games. This system has four levels. In
    order, they are:

    - "thread" (verifies that the context is an UNO game thread)
    - "player" (verifies that the invoker is a player in the UNO game)
    - "game" (verifies that the game has been started)
    - "turn" (verifies that it's the invoking players turn)


    Each verification level is inclusive of all previous ones, and *all* verification checks for the specified level
    must pass in order for the decorated command to execute.

    If the ``verify_host`` flag is set to True, the decorator will also check that the invoking user is the Game Host;
    this, however, is independent of the four verificiation levels described above.

    :param level: The verification level.
    :param verify_host: Whether or not to verify that the invoking user is the Game Host.
    """

    async def predicate(ctx: discord.ApplicationContext):
        command_name = f"`/{ctx.command.qualified_name}`"

        async def is_uno_thread():
            if uno.UnoGame.retrieve_game(ctx.channel_id):
                return True
            else:
                message = (
                    f"You can only use {command_name} in designated UNO game threads. "
                    f"Head to a game thread and try again."
                )
                embed = discord.Embed(
                    title="You can't do that here.",
                    description=message,
                    color=support.Color.red(),
                )
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        async def is_player():
            game = uno.UnoGame.retrieve_game(ctx.channel_id)

            if any(
                player
                for player in game.players.itervalues()
                if player.user == ctx.user
            ):
                return True
            else:
                message = f"Only players in this UNO game can use {command_name}."
                embed = discord.Embed(
                    title="You're not playing in this game.",
                    description=message,
                    color=support.Color.red(),
                )
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        async def is_active_game():
            game = uno.UnoGame.retrieve_game(ctx.channel_id)

            if not game.is_joinable:
                return True
            else:
                message = (
                    f"You can't use {command_name} until the game has started. Wait until the Game Host starts "
                    f"the game, then try again."
                )
                embed = discord.Embed(
                    title="This game hasn't started yet.",
                    description=message,
                    color=support.Color.red(),
                )
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        async def is_player_turn():
            game = uno.UnoGame.retrieve_game(ctx.channel_id)

            if game.current_player.value.user == ctx.user:
                return True
            else:
                message = f"You can only use {command_name} when it's your turn. Wait your turn, then try again."
                embed = discord.Embed(
                    title="It's not your turn.",
                    description=message,
                    color=support.Color.red(),
                )
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        async def verify_is_host():
            game = uno.UnoGame.retrieve_game(ctx.channel_id)

            if game.host == ctx.user:
                return True
            else:
                message = (
                    f"Only the Game Host for this UNO game can use {command_name}."
                )
                embed = discord.Embed(
                    title="You're not the Game Host.",
                    description=message,
                    color=support.Color.red(),
                )
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        checks = {
            "thread": is_uno_thread(),
            "player": is_player(),
            "game": is_active_game(),
            "turn": is_player_turn(),
        }

        success = False

        for key, check in checks.items():
            success = await check

            if not success or key == level:
                break

        # we only want to bother verifying the game host if all the other checks passed
        if success and verify_host:
            success = await verify_is_host()

        return success

    return commands.check(predicate)
