########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import discord
from discord import Option

import support
from bot import bot
from cogs import rps
from cogs.base import Cog
from support import SlashCommandGroup


@bot.register_cog
class RPSCog(Cog):
    """
    Commands for Rock-Paper-Scissors.
    """

    rps_group = SlashCommandGroup("rps", "Commands for playing Rock-Paper-Scissors.")

    @rps_group.command(
        description="Challenge someone to a game of Rock-Paper-Scissors."
    )
    @support.not_in_maintenance()
    @support.bot_has_permissions(support.GamePermissions.rps())
    async def challenge(
        self,
        ctx: discord.ApplicationContext,
        opponent: Option(discord.User, "Mention a player to be your opponent."),
        game_format: Option(
            str,
            name="format",
            description="Choose whether to play a best-of-three, best-of-five, "
            "or best-of-nine match.",
            choices=["Best of Three", "Best of Five", "Best of Nine"],
        ),
    ):
        """
        Challenge a user to a Rock-Paper-Scissors game between themselves and the command invoker.

        Parameters
        ----------
        ctx : discord.ApplicationContext
            The invocation context.
        opponent : discord.User
            The user to challenge to a Rock-Paper-Scissors game.
        game_format : str
            The game format. Must be one of "Best of Three", "Best of Five", or "Best of Nine".
        """
        # the user cannot challenge themselves
        if ctx.user == opponent:
            msg = "You can't play with yourself. Choose someone else to challenge."
            embed = discord.Embed(
                title="Make some friends, please.",
                description=msg,
                color=support.Color.error(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # the user cannot challenge the bot
        elif opponent == ctx.me:
            msg = (
                "Unfortunately, my creator is too merciful to allow me to utterly decimate you at "
                "Rock-Paper-Scissors.\n"
                "\n"
                "Challenge someone else."
            )
            embed = discord.Embed(
                title="Not happening.", description=msg, color=support.Color.error()
            )
            await ctx.respond(embed=embed, ephemeral=True)

        # the user cannot challenge other bots
        elif opponent.bot:
            msg = (
                "You can only play with real people. Choose someone else to challenge."
            )
            embed = discord.Embed(
                title="That's a bot.", description=msg, color=support.Color.error()
            )
            await ctx.respond(embed=embed, ephemeral=True)

        else:
            # map game formats to the number of points needed for victory in each
            victory_points = {"Best of Three": 2, "Best of Five": 3, "Best of Nine": 5}

            # create the game object
            rps_game = rps.RPSGame(
                players=[rps.RPSPlayer(ctx.user), rps.RPSPlayer(opponent)],
                game_format=game_format,
                points_to_win=victory_points[game_format],
            )

            challenge_acceptance = await rps_game.issue_challenge(ctx)

            if challenge_acceptance:

                await rps_game.game_intro(ctx)

                while True:
                    move_selection_complete = await rps_game.select_player_moves(ctx)
                    if not move_selection_complete:
                        break
                    else:
                        await rps_game.report_round_results(ctx)

                        match_winner = rps_game.check_for_match_winner()

                        if match_winner:
                            await rps_game.end_match(ctx, match_winner)
                            break
                        else:
                            rps_game.current_round += 1
