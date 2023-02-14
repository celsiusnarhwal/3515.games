########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import discord
from discord.ext import commands

import support
from cogs import cah

# decorators


def verify_context(
    level: str, *, verify_host: bool = False, is_pseudocommand: bool = False
):
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

    async def predicate(ctx: discord.ApplicationContext) -> bool:
        command_name = ctx.command.qualified_name

        if is_pseudocommand:
            command_name += f" > {ctx.selected_options[0]['value']}"

        command_name = f"`/{command_name}`"

        async def is_cah_thread() -> bool:
            if not cah.CAHGame.retrieve_game(ctx.channel_id):
                message = (
                    f"You can only use {command_name} in designated CAH game threads. "
                    f"Head to a game thread and try again."
                )
                embed = discord.Embed(
                    title="You can't do that here.",
                    description=message,
                    color=support.Color.error(),
                )
                await ctx.respond(embed=embed, ephemeral=True)

                return False

            return True

        async def is_player() -> bool:
            game = cah.CAHGame.retrieve_game(ctx.channel_id)

            if not any(
                player
                for player in game.players.itervalues()
                if player.user == ctx.user
            ):
                message = f"Only players in this CAH game can use {command_name}."
                embed = discord.Embed(
                    title="You're not playing in this game.",
                    description=message,
                    color=support.Color.error(),
                )
                await ctx.respond(embed=embed, ephemeral=True)

                return False

            return True

        async def is_active_game() -> bool:
            game = cah.CAHGame.retrieve_game(ctx.channel_id)

            if game.is_joinable:
                message = (
                    f"You can't use {command_name} until the game has started. Wait until the Game Host starts "
                    f"the game, then try again."
                )
                embed = discord.Embed(
                    title="This game hasn't started yet.",
                    description=message,
                    color=support.Color.error(),
                )
                await ctx.respond(embed=embed, ephemeral=True)

                return False

            return True

        async def is_player_turn() -> bool:
            async def czar_mode() -> bool:
                if game.is_voting:
                    if game.card_czar.value != player:
                        message = "Please wait for the Card Czar to finish."
                        embed = discord.Embed(
                            title="It's voting time.",
                            description=message,
                            color=support.Color.error(),
                        )
                        await ctx.respond(embed=embed, ephemeral=True)

                        return False
                else:
                    if game.card_czar.value == player:
                        message = f"As the Card Czar, you can't use {command_name} until it's voting time."
                        embed = discord.Embed(
                            title="Patience, young Padawan.",
                            description=message,
                            color=support.Color.error(),
                        )
                        await ctx.respond(embed=embed, ephemeral=True)

                        return False
                    elif player.has_submitted:
                        message = "Please wait for the other players to finish."
                        embed = discord.Embed(
                            title="You've already made your submission.",
                            description=message,
                            color=support.Color.error(),
                        )
                        submission = discord.utils.find(
                            lambda c: c.player == player, game.candidates
                        )
                        embed.add_field(name="Your Submission", value=submission.text)
                        await ctx.respond(embed=embed, ephemeral=True)

                        return False

                return True

            async def popular_vote_mode() -> bool:
                if game.is_voting:
                    if player.has_voted:
                        message = "Please wait for the other players to finish."
                        embed = discord.Embed(
                            title="You've already cast your vote.",
                            description=message,
                            color=support.Color.error(),
                        )
                        vote = discord.utils.find(
                            lambda c: player in c.voters, game.candidates
                        )
                        embed.add_field(name="Your Vote", value=vote.text)
                        await ctx.respond(embed=embed, ephemeral=True)

                        return False

                elif player.has_submitted:
                    message = "Please wait for the other players to finish."
                    embed = discord.Embed(
                        title="You've already made your submission.",
                        description=message,
                        color=support.Color.error(),
                    )
                    submission = discord.utils.find(
                        lambda c: c.player == player, game.candidates
                    )
                    embed.add_field(name="Your Submission", value=submission.text)
                    await ctx.respond(embed=embed, ephemeral=True)

                    return False

                return True

            game = cah.CAHGame.retrieve_game(ctx.channel_id)
            player = game.retrieve_player(ctx.user)

            return (
                await czar_mode()
                if game.settings.use_czar
                else await popular_vote_mode()
            )

        async def verify_is_host() -> bool:
            game = cah.CAHGame.retrieve_game(ctx.channel_id)

            if game.host != ctx.user:
                message = (
                    f"Only the Game Host for this CAH game can use {command_name}."
                )
                embed = discord.Embed(
                    title="You're not the Game Host.",
                    description=message,
                    color=support.Color.error(),
                )
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
