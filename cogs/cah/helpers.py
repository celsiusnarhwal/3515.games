########################################################################################################################
#                         Copyright (C) 2022-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import alianator
import discord
from discord.ext import commands

import support
from cogs import cah


# decorators


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

       If the ``verify_host`` flag is set to True, the decorator will also check that the invoking user is
       the Game Host; this, however, is independent of the four verificiation levels described above.

       :param level: The verification level.
       :param verify_host: Whether or not to verify that the invoking user is the Game Host.
       """

    async def predicate(ctx: discord.ApplicationContext):
        command_name = f"`/{ctx.command.qualified_name}`"

        async def is_cah_thread():
            if not cah.CAHGame.retrieve_game(ctx.channel_id):
                message = f"You can only use {command_name} in designated CAH game threads. " \
                          f"Head to a game thread and try again."
                embed = discord.Embed(title="You can't do that here.", description=message,
                                      color=support.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)

                return False

            return True

        async def is_player():
            game = cah.CAHGame.retrieve_game(ctx.channel_id)

            if not any(player for player in game.players.itervalues() if player.user == ctx.user):
                message = f"Only players in this CAH game can use {command_name}."
                embed = discord.Embed(title="You're not playing in this game.", description=message,
                                      color=support.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)

                return False

            return True

        async def is_active_game():
            game = cah.CAHGame.retrieve_game(ctx.channel_id)

            if game.is_joinable:
                message = f"You can't use {command_name} until the game has started. Wait until the Game Host starts " \
                          f"the game, then try again."
                embed = discord.Embed(title="This game hasn't started yet.", description=message,
                                      color=support.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)

                return False

            return True

        async def is_player_turn():
            async def to_play_cards():
                if player != game.card_czar.value:
                    if game.is_voting:
                        message = f"You can't use {command_name} until voting has finished."
                        embed = discord.Embed(title="You can't do that right now.", description=message,
                                              color=support.Color.red())
                        await ctx.respond(embed=embed, ephemeral=True)

                        return False
                    elif player.has_submitted:
                        message = "Please wait for the other players to finish."
                        embed = discord.Embed(title="You've already made your submission.", description=message,
                                              color=support.Color.red())
                        submission = discord.utils.find(lambda c: c.player == player, game.candidates)
                        embed.add_field(name="Your Submission", value=submission.text)
                        await ctx.respond(embed=embed, ephemeral=True)

                        return False
                else:
                    message = f"You can only use {command_name} when you're not the Card Czar."
                    embed = discord.Embed(title="You can't do that right now.", description=message,
                                          color=support.Color.red())
                    await ctx.respond(embed=embed, ephemeral=True)

                    return False

                return True

            async def to_czar_vote():
                if game.card_czar.value == player:
                    if not game.is_voting:
                        message = "Wait until it's voting time, then try again."
                        embed = discord.Embed(title="You can't do that right now.", description=message,
                                              color=support.Color.red())
                        await ctx.respond(embed=embed, ephemeral=True)

                        return False
                else:
                    message = f"You can only use {command_name} when you're the Card Czar."
                    embed = discord.Embed(title="You're not the Card Czar.", description=message,
                                          color=support.Color.red())
                    await ctx.respond(embed=embed, ephemeral=True)

                    return False

                return True

            async def to_popular_vote():
                if game.is_voting:
                    if player.has_voted:
                        message = "Please wait for the other players to finish."
                        embed = discord.Embed(title="You've already cast your vote.", description=message,
                                              color=support.Color.red())
                        await ctx.respond(embed=embed, ephemeral=True)

                        return False
                else:
                    message = "Wait until it's voting time, then try again."
                    embed = discord.Embed(title="You can't do that right now.", description=message,
                                          color=support.Color.red())
                    await ctx.respond(embed=embed, ephemeral=True)

                    return False

                return True

            game = cah.CAHGame.retrieve_game(ctx.channel_id)
            player = game.retrieve_player(ctx.user)

            if ctx.command.name == "play":
                return await to_play_cards()
            elif ctx.command.name == "vote":
                if game.settings.use_czar:
                    return await to_czar_vote()
                else:
                    return await to_popular_vote()

        async def verify_is_host():
            game = cah.CAHGame.retrieve_game(ctx.channel_id)

            if game.host != ctx.user:
                message = f"Only the Game Host for this CAH game can use {command_name}."
                embed = discord.Embed(title="You're not the Game Host.", description=message,
                                      color=support.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)

                return False

            return True

        checks = {
            "thread": is_cah_thread,
            "player": is_player,
            "game": is_active_game,
            "turn": is_player_turn,
        }

        success = False

        for key, check in checks.items():
            success = await check()

            if not success or key == level:
                break

        # we only want to bother verifying the game host if all the other checks passed
        if success and verify_host:
            success = await verify_is_host()

        return success

    return commands.check(predicate)


# miscellaneous

async def check_voice_permissions(ctx: discord.ApplicationContext):
    """
    Checks that the bot has the necessary permissions to create a voice channel for a CAH game.
    """
    if ctx.guild.me.guild_permissions >= support.GamePermissions.cah_voice():
        return True
    else:
        message = "In order to create a voice channel for your Cards Against Humanity game, I need the following " \
                  "permissions __at the server level__:\n\n"

        message += "\n".join(
            f"- {p}" for p in alianator.resolve(support.GamePermissions.cah_voice() - ctx.guild.me.guild_permissions)
        )

        message += f"\n\n Once I've been given those permissions, try again.\n" \
                   f"\n" \
                   f"(You can also opt to create a game without a voice channel - just set the `voice` option to " \
                   f"`Don't Create` when using `/{ctx.command.qualified_name}`.)"

        embed = discord.Embed(title="I need more power!", description=message, color=support.Color.red())

        await ctx.respond(embed=embed, ephemeral=True)
