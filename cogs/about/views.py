########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import os
import platform
import time

import discord
import tomlkit as toml
from discord import Interaction, ButtonStyle
from discord.ui import Button, button as discord_button

import support
import uptime
from support.views import EnhancedView


class AboutView(EnhancedView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_item(Button(label="3515.games", emoji="🌐", url="https://3515.games", row=0))
        self.add_item(Button(label="Add me to your server!", emoji="👋🏾", url="https://invite.3515.games", row=1))
        self.add_item(Button(label="Support my development!", emoji="🔨", url="https://3515.games/donate", row=1))
        self.add_item(Button(label="Legal Information", emoji="🏛", url="https://3515.games/legal", row=2))

    @discord_button(label="Credits", emoji="🎬", style=ButtonStyle.gray)
    async def credits(self, button: Button, interaction: Interaction):
        class CreditsView(EnhancedView):
            @discord_button(label="Back", style=ButtonStyle.red)
            async def back(self, button: Button, interaction: Interaction):
                await AboutView(ctx=self.ctx).show_about(interaction)

        with support.Assets.about():
            credits_text = open(os.path.join("pages", "credits.md")).read()
            embed = discord.Embed(title="Credits", description=credits_text, color=support.Color.mint())

            original_message = await self.ctx.interaction.original_message()
            embed.set_author(name="About", icon_url=original_message.author.display_avatar.url)

            await interaction.response.defer()
            await original_message.edit(embed=embed, attachments=[], view=CreditsView(ctx=self.ctx))

    @discord_button(label="Technical Data", emoji="💻", style=ButtonStyle.gray)
    async def technical(self, button: Button, interaction: Interaction):
        class TechnicalView(EnhancedView):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.add_item(Button(label="Source Code", emoji="<:github:953746341413142638>",
                                     url="https://code.3515.games"))

            @discord_button(label="Back", style=ButtonStyle.red)
            async def back(self, button: Button, interaction: Interaction):
                await AboutView(ctx=self.ctx).show_about(interaction)

        statistics = {
            "Bot Version": toml.load("pyproject.toml")["tool"]["poetry"]["version"],
            "Python Version": platform.python_version(),
            "Pycord Version": discord.__version__,
            "Uptime": uptime.get_uptime(),
            "Ping": "Calculating...",
        }

        embed = discord.Embed(title="Technical Data", description="Statistics for nerds.", color=support.Color.mint())

        for index, (stat, value) in enumerate(statistics.items()):
            embed.add_field(name=stat, value=value, inline=True)

            if index % 2 == 1:
                embed.add_field(name="\u200b", value="\u200b")

        original_message = await self.ctx.interaction.original_message()
        embed.set_author(name="About", icon_url=original_message.author.display_avatar.url)

        ping_start = time.perf_counter()
        await interaction.response.defer()
        await original_message.edit(embed=embed, attachments=[], view=TechnicalView(ctx=self.ctx))
        ping_end = time.perf_counter()

        embed.set_field_at(index=6, name="Ping", value=f"{round(ping_end - ping_start, 3)}s")
        await original_message.edit(embed=embed)

    # @discord_button(label="Add me to your server!", style=ButtonStyle.gray, row=2)
    # async def invite(self, button: Button, interaction: Interaction):
    #     class InviteView(EnhancedView):
    #         def __init__(self, **kwargs):
    #             super().__init__(**kwargs)
    #
    #             oauth_url = "https://discordapp.com/oauth2/authorize?"
    #             params = {
    #                 "client_id": self.ctx.bot.user.id,
    #                 "scope": "bot",
    #                 "permissions": support.GamePermissions.everything().value,
    #             }
    #
    #             self.add_item(Button(label="Invite Me", emoji="🔗", url=oauth_url + urllib.parse.urlencode(params)))
    #
    #         @discord_button(label="Back", style=ButtonStyle.red)
    #         async def back(self, button: Button, interaction: Interaction):
    #             await AboutView(ctx=self.ctx).show_about(interaction)
    #
    #     msg = "Wanna add me to your server? I'm flattered. 😊\n" \
    #           "\n" \
    #           "To invite me, use the button below or visit [3515.games/invite](https://3515.games/invite) " \
    #           "in your browser. (Note that everyone in the server you invite me to will become subject to " \
    #           "my [Privacy Policy](https://3515.games/privacy).)"
    #
    #     embed = discord.Embed(title="Invite Me", description=msg, color=support.Color.mint())
    #
    #     original_message = await self.ctx.interaction.original_message()
    #     embed.set_author(name="About", icon_url=original_message.author.display_avatar.url)
    #
    #     await interaction.response.defer()
    #     await interaction.edit_original_message(embed=embed, attachments=[], view=InviteView(ctx=self.ctx))

    async def show_about(self, interaction: Interaction = None):
        with support.Assets.about():
            about_text = open(os.path.join("pages", "main.md")).read()

        about_embed = discord.Embed(title="About Me", description=about_text,
                                    color=support.Color.mint())

        with support.Assets.about():
            bot_logo = discord.File("bot_logo.png", filename="bot_logo.png")
            about_embed.set_image(url="attachment://bot_logo.png")
            if interaction:
                await interaction.response.defer()
                await interaction.edit_original_message(embed=about_embed, file=bot_logo, attachments=[], view=self)
            else:
                await self.ctx.respond(embed=about_embed, file=bot_logo, view=self, ephemeral=True)
