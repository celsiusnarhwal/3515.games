########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import discord
from clockworks import clock
from cogs import cah, misc, uno
from cogs.base import Cog
from discord import Interaction
from discord.ext import commands
from discord.ui import InputText, Modal
from wonderwords import RandomWord

import support
from bot import bot
from support import slash_command


@bot.register_cog
class MiscCog(Cog):
    """
    A cog to contain miscellaneous, standalone, commands that don't fit in any of the other cogs.
    """

    @slash_command(description="Allow me to reintroduce myself.")
    async def about(self, ctx: discord.ApplicationContext):
        await misc.AboutView(ctx=ctx).present()

    @slash_command(description="Get some.")
    async def help(self, ctx: discord.ApplicationContext):
        await misc.HelpView(ctx=ctx).present(ctx)

    @slash_command(
        description="See which games I have the necessary permissions to play."
    )
    async def caniplay(self, ctx: discord.ApplicationContext):
        games = {
            "Rock-Paper-Scissors": support.GamePermissions.rps(),
            "UNO": support.GamePermissions.uno(),
            "Chess": support.GamePermissions.chess(),
            "Cards Against Humanity": support.GamePermissions.cah(),
        }

        msg = (
            "Each of my games requires a different set of permissions to play. Given the permissions I have in "
            "this channel, here are the games I can and can't play:\n\n"
        )

        for game, permset in games.items():
            msg += f"{game}: {'✅' if ctx.channel.permissions_for(ctx.me) >= permset else '❌'}\n"

        msg += (
            "\nKeep in mind that server moderators can directly control access to my commands via "
            "Server Settings and I have no way of knowing if any of my commands have been disabled on a server "
            "level, so a checkmark here doesn't guarantee that game can actually be played."
        )

        embed = discord.Embed(
            title="Can I play that?", description=msg, color=support.Color.mint()
        )

        await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(
        description="Create a voice channel for a supported game. You won't be able to delete this channel manually."
    )
    async def voice(self, ctx: discord.ApplicationContext):
        supported_games: list[support.HostedGame] = [
            uno.UnoGame,
            cah.CAHGame,
        ]

        for game in supported_games:
            game_obj = game.retrieve_game(ctx.channel_id)
            if game_obj:
                if game_obj.host == ctx.user:
                    channel = await game_obj.create_voice_channel()
                    msg = (
                        f"Your voice channel is {channel.mention}.\n As the Game Host, you can mute and defean the "
                        f"channel's members and even use Priority Speaker. Try it out!\n"
                        f"\n"
                        f"Other players will get access to this channel as soon as they join the game."
                    )

                    embed = discord.Embed(
                        title="Voice channel created!",
                        description=msg,
                        color=support.Color.mint(),
                    )
                    await ctx.respond(embed=embed, ephemeral=True)

                    msg = (
                        f"Players can access {channel.mention} after joining the game."
                    )
                    embed = discord.Embed(
                        title="Voice channel created!",
                        description=msg,
                        color=support.Color.mint(),
                    )

                    await game_obj.thread.send(
                        embed=embed, view=support.GameVoiceURLView(channel)
                    )
                else:
                    msg = "Only the Game Host can create a voice channel for this game."
                    embed = discord.Embed(
                        title="You're not the Game Host.",
                        description=msg,
                        color=support.Color.error(),
                    )

                    await ctx.respond(embed=embed, ephemeral=True)
                break
        else:
            msg = (
                "To create a voice channel, you must use this command in the game thread of a supported game of "
                "which you are the Game Host. Currently, supported games include:\n\n"
            )

            for game in supported_games:
                msg += f"- {game.name}"
                if game is not supported_games[-1]:
                    msg += "\n"

            embed = discord.Embed(
                title="You can't do that here.",
                description=msg,
                color=support.Color.error(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

    @slash_command(description="秘密 だ。")
    @support.is_celsius_narhwal()
    async def kurumi(self, ctx: discord.ApplicationContext):
        wordsmith = RandomWord()
        passphrase = " ".join(wordsmith.random_words(4))

        class WalnutModal(Modal):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                self.add_item(
                    InputText(
                        label="Passphrase",
                        custom_id="passphrase",
                        placeholder=passphrase,
                    )
                )

            async def callback(this, interaction: Interaction):
                if this.children[0].value == passphrase:
                    clock().start_maintenance()

                    await self.bot.change_presence(
                        activity=discord.Activity(
                            type=discord.ActivityType.playing,
                            name="in Maintenance Mode 🚧",
                        )
                    )

                    await interaction.response.send_message(
                        "Maintenance mode started.", ephemeral=True
                    )
                else:
                    await interaction.response.send_message(
                        "Incorrect passphrase.", ephemeral=True
                    )

        if not clock().maintenance_start_time:
            modal = WalnutModal(title="Enter Maintenance Mode")
            await ctx.send_modal(modal)
        else:
            embed = discord.Embed(
                title="Road work ahead.",
                description="Maintenance mode is already active.",
                color=support.Color.orange(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

    @commands.Cog.listener(name="on_guild_channel_delete")
    async def on_guild_channel_delete(self, channel: discord.VoiceChannel):
        if type(channel) == discord.VoiceChannel:
            if (
                channel.category.name.casefold() == "3515.games"
                and len(channel.category.channels) == 0
            ):
                await channel.category.delete()
