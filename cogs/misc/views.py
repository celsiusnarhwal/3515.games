########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import os
import platform

import discord
import inflect as ifl
from discord import ButtonStyle, Interaction
from discord.ui import Button
from discord.ui import button as discord_button

import support
import uptime
from support.views import View

inflect = ifl.engine()


class AboutView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_item(
            Button(label="www.3515.games", emoji="🌐", url="https://3515.games", row=0)
        )
        self.add_item(
            Button(
                label="Terms",
                emoji="🏛",
                url="https://3515.games/legal/terms",
                row=1,
            )
        )
        self.add_item(
            Button(
                label="Privacy",
                emoji="🔒",
                url="https://3515.games/legal/privacy",
                row=1,
            )
        )
        self.add_item(
            Button(
                label="Acknowledgements",
                url="https://3515.games/legal/acknowledgements",
                row=1,
            )
        )

    @discord_button(label="Credits", emoji="🎬", style=ButtonStyle.gray)
    async def credits(self, _, interaction: Interaction):
        class CreditsView(View):
            @discord_button(label="Back", style=ButtonStyle.red)
            async def back(self, _, interaction: Interaction):
                await AboutView(ctx=self.ctx).present(interaction)

        with support.Assets.misc():
            credits_text = open(os.path.join("pages", "credits.md")).read()
            embed = discord.Embed(
                title="Credits", description=credits_text, color=support.Color.mint()
            )

            original_message = await self.ctx.interaction.original_message()
            embed.set_author(
                name="About", icon_url=original_message.author.display_avatar.url
            )

            await interaction.response.defer()
            await original_message.edit(
                embed=embed, attachments=[], view=CreditsView(ctx=self.ctx)
            )

    @discord_button(label="Technical Data", emoji="💻", style=ButtonStyle.gray)
    async def technical(self, _, interaction: Interaction):
        class TechnicalView(View):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.add_item(
                    Button(
                        label="Source Code",
                        emoji="<:github:953746341413142638>",
                        url="https://code.3515.games",
                    )
                )

            @discord_button(label="Back", style=ButtonStyle.red)
            async def back(self, _, interaction: Interaction):
                await AboutView(ctx=self.ctx).present(interaction)

        statistics = {
            "Bot Version": support.poetry()["version"],
            "Python Version": platform.python_version(),
            "Pycord Version": discord.__version__,
            "Uptime": uptime.get_uptime(),
            "Ping": f"{inflect.no('second', round(self.ctx.bot.latency, 2))}",
        }

        embed = discord.Embed(
            title="Technical Data",
            description="Statistics for nerds.",
            color=support.Color.mint(),
        )

        for index, (stat, value) in enumerate(statistics.items()):
            embed.add_field(name=stat, value=value, inline=True)

            if (index + 1) % 2 == 0:
                embed.add_field(name="\u200b", value="\u200b")

        original_message = await self.ctx.interaction.original_response()
        embed.set_author(
            name="About", icon_url=original_message.author.display_avatar.url
        )

        await interaction.response.defer()
        await original_message.edit(
            embed=embed, attachments=[], view=TechnicalView(ctx=self.ctx)
        )

    async def present(self, interaction: Interaction = None):
        with support.Assets.misc():
            about_text = open(os.path.join("pages", "main.md")).read()

        about_embed = discord.Embed(
            title="About Me", description=about_text, color=support.Color.mint()
        )

        with support.Assets.misc():
            bot_logo = discord.File("bot_logo.png", filename="bot_logo.png")
            about_embed.set_image(url="attachment://bot_logo.png")
            if interaction:
                await interaction.response.defer()
                await interaction.edit_original_response(
                    embed=about_embed, file=bot_logo, attachments=[], view=self
                )
            else:
                await self.ctx.respond(
                    embed=about_embed, file=bot_logo, view=self, ephemeral=True
                )
