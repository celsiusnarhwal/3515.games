########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import discord
from discord import Option

import shrine
import support
from bot import bot
from cogs.base import Cog
from support import SlashCommandGroup


@bot.register_cog
class ClarisCog(Cog):
    """
    Commands and listeners for Connect 4.
    """

    claris_group = SlashCommandGroup("claris", "Commands for playing Connect 4.")

    @claris_group.command()
    @support.not_in_maintenance()
    @support.bot_has_permissions(support.GamePermissions.claris())
    @support.invoked_in_text_channel()
    async def challenge(
        self,
        ctx: discord.ApplicationContext,
        opponent: Option(discord.User, "Mention a user to be your opponent."),
    ):
        """
        Challenge someone to a game of Connect 4.
        """
        if ctx.user == opponent:
            msg = "You can't play with yourself. Choose someone else to challenge."
            embed = discord.Embed(
                title="Make some friends, please.",
                description=msg,
                color=support.Color.error(),
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        elif opponent == ctx.me:
            msg = "Challenge someone else."
            embed = discord.Embed(
                title="lol no", description=msg, color=support.Color.error()
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        elif opponent.bot:
            msg = (
                "You can only play with real people. Choose someone else to challenge."
            )
            embed = discord.Embed(
                title="That's a bot.", description=msg, color=support.Color.error()
            )
            await ctx.respond(embed=embed, ephemeral=True)
            return

        if not ...:  # TODO: replace with duplicate game check
            ...
        else:
            with shrine.Torii.claris() as torii:
                template = torii.get_template("create-game.md")
                msg = template.render(opponent=opponent)

            embed = discord.Embed(
                title="Creating a Connect 4 Game",
                description=msg,
                color=support.Color.caution(),
            )

            view = support.ConfirmationView(ctx=ctx)
            challenge_confirmation = await view.request_confirmation(
                prompt_embeds=[embed], ephemeral=True
            )

            if challenge_confirmation:
                await ctx.interaction.edit_original_response(
                    content=f"Waiting on {opponent.mention}...",
                    embeds=[],
                    view=None,
                )

                view = support.GameChallengeResponseView(
                    ctx=ctx,
                    target_user=opponent,
                    challenger=ctx.user,
                    game_name="Connect 4",
                )

                challenge_acceptance = await view.request_response()

                if not challenge_acceptance:
                    return
                elif challenge_confirmation is not None:
                    await ctx.interaction.edit_original_response(
                        content="Okay! Your challenge was canceled.",
                        embeds=[],
                        view=None,
                    )
                    return

            # TODO write game creation logic
