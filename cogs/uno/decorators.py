from __future__ import annotations

import discord
from discord.ext import commands

import support
from cogs import uno


def verify_context(level: str):
    """
    A decorator which implements a tiered context verification system for UNO games. This system has four levels. In
    order, they are:

    - "thread" (verifies that the context is an UNO game thread)
    - "player" (verifies that the invoker is a player in the UNO game)
    - "game" (verifies that the game has been started)
    - "turn" (verifies that it's the invoking players turn)

    Each verification level is inclusive of all previous ones, and *all* verification checks for the specified level
    must pass in order for the decorated command to execute.

    :param level: The verification level.
    """

    async def predicate(ctx: discord.ApplicationContext):
        success = False
        command_name = f"`/{ctx.command.qualified_name}`"

        async def is_uno_thread():
            if uno.UnoGame.retrieve_game(ctx.channel_id):
                return True
            else:
                message = f"You can only use {command_name} in designated UNO game threads. " \
                          f"Head to a game thread and try again."
                embed = discord.Embed(title="You can't do that here.", description=message,
                                      color=support.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        async def is_player():
            game = uno.UnoGame.retrieve_game(ctx.channel_id)

            if any(player for player in game.players.itervalues() if player.user == ctx.user):
                return True
            else:
                message = f"Only players in this UNO game can use {command_name}."
                embed = discord.Embed(title="You're not playing in this game.", description=message,
                                      color=support.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        async def is_active_game():
            game = uno.UnoGame.retrieve_game(ctx.channel_id)

            if not game.is_joinable:
                return True
            else:
                message = f"You can't use {command_name} until the game has started. Wait until the Game Host starts " \
                          f"the game, then try again."
                embed = discord.Embed(title="This game hasn't started yet.", description=message,
                                      color=support.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        async def is_player_turn():
            game = uno.UnoGame.retrieve_game(ctx.channel_id)

            if game.current_player.value.user == ctx.user:
                return True
            else:
                message = f"You can only use {command_name} when it's your turn. Wait your turn, then try again."
                embed = discord.Embed(title="It's not your turn.", description=message,
                                      color=support.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        checks = {
            "thread": is_uno_thread(),
            "player": is_player(),
            "game": is_active_game(),
            "turn": is_player_turn(),
        }

        for key, check in checks.items():
            success = await check

            if not success or key == level:
                break

        return success

    return commands.check(predicate)


def verify_host_uniqueness():
    """
    A decorator used to check that a user attempting to create an UNO game is not already hosting one in the same
    server.
    """

    async def predicate(ctx: discord.ApplicationContext):
        user_hosted_game = uno.UnoGame.find_hosted_games(user=ctx.user, guild_id=ctx.guild_id)

        if not user_hosted_game:
            return True
        else:
            message = "You're already hosting an UNO game in this server. Before you can create a new one, you must " \
                      "either complete, end, or transfer host powers for your current game.\n"
            embed = discord.Embed(title="You're already hosting a game.", description=message,
                                  color=support.Color.red())
            game_thread_url = f"https://discord.com/channels/{ctx.guild_id}/{user_hosted_game.thread.id}"
            await ctx.respond(embed=embed, view=uno.GoToUnoThreadView(game_thread_url), ephemeral=True)

            return False

    return commands.check(predicate)


def verify_is_host():
    """
    A decorator used to check that a command is being used by an UNO Game Host before executing it.
    """

    async def predicate(ctx: discord.ApplicationContext):
        game = uno.UnoGame.retrieve_game(ctx.channel_id)
        command_name = f"`/{ctx.command.qualified_name}`"

        if game.host == ctx.user:
            return True
        else:
            message = f"Only the Game Host for this UNO game can use {command_name}."
            embed = discord.Embed(title="You're not the Game Host.", description=message,
                                  color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

            return False

    return commands.check(predicate)
