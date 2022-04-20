from __future__ import annotations

import json
import os
import platform
import textwrap

import discord
import toml
from discord import Interaction, ButtonStyle
from discord.ext import pages as discord_pages
from discord.ui import Button, button as discord_button

import support
from support.views import EnhancedView
import uptime


class AboutView(EnhancedView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @discord_button(label="Credits", style=ButtonStyle.gray)
    async def credits(self, button: Button, interaction: Interaction):
        with support.Assets.about():
            credits_text = open(os.path.join("pages", "credits.md")).read()
            embed = discord.Embed(title="Credits", description=credits_text, color=support.Color.mint())

            original_message = await self.ctx.interaction.original_message()
            embed.set_author(name="About - Credits", icon_url=original_message.author.display_avatar.url)

            await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord_button(label="Legal", style=ButtonStyle.gray)
    async def legal(self, button: Button, interaction: Interaction):
        class LegalView(EnhancedView):
            @discord_button(label="Privacy Policy", style=ButtonStyle.gray)
            async def privacy_policy(self, button: Button, interaction: Interaction):
                with support.Assets.about():
                    privacy_text = open(os.path.join("pages", "legal", "privacy.md")).read()
                    embed = discord.Embed(title="Privacy Policy", description=privacy_text, color=support.Color.mint())

                    original_message = await self.ctx.interaction.original_message()
                    embed.set_author(name="Legal",
                                     icon_url=original_message.author.display_avatar.url)

                    await interaction.response.send_message(embed=embed, ephemeral=True)

            @discord_button(label="Intellectual Property", style=ButtonStyle.gray)
            async def ip_acknowledgements(self, button: Button, interaction: Interaction):
                with support.Assets.about():
                    ip_text = open(os.path.join("pages", "legal", "ip.md")).read()
                    embed = discord.Embed(title="Intellectual Property", description=ip_text,
                                          color=support.Color.mint())

                    original_message = await self.ctx.interaction.original_message()
                    embed.set_author(name="Legal",
                                     icon_url=original_message.author.display_avatar.url)

                    await interaction.response.send_message(embed=embed, ephemeral=True)

            @discord_button(label="Software Licenses", style=ButtonStyle.gray)
            async def software_licenses(self, button: Button, interaction: Interaction):
                with support.Assets.about():
                    oss_text = open(os.path.join("pages", "legal", "oss.md")).read()
                    embed = discord.Embed(title="Software Licenses", description=oss_text, color=support.Color.mint())

                    original_message = await self.ctx.interaction.original_message()
                    embed.set_author(name="Legal",
                                     icon_url=original_message.author.display_avatar.url)

                    licenses = json.load(open("licenses.json"))

                    pages = [embed]

                    for oss_license in licenses:
                        page_title = oss_license["Name"]
                        page_text = f"**{oss_license['License']}**\n\n{oss_license['LicenseText']}"

                        split_page_text = textwrap.wrap(page_text, 2000, break_long_words=False,
                                                        replace_whitespace=False)

                        embeds = []
                        for index, text in enumerate(split_page_text):

                            if index == 1:
                                page_title += " (cont.)"

                            e = discord.Embed(title=page_title, description=text, color=support.Color.mint())
                            e.set_author(name="Software Licenses",
                                         icon_url=original_message.author.display_avatar.url)

                            embeds.append(e)

                        pages.extend(embeds)

                    paginator = discord_pages.Paginator(pages=pages, use_default_buttons=False,
                                                        custom_buttons=support.paginator_emoji_buttons())

                    await paginator.respond(interaction, ephemeral=True)

        with support.Assets.about():
            legal_text = open(os.path.join("pages", "legal.md")).read()
            embed = discord.Embed(title="Legal", description=legal_text, color=support.Color.mint())

            original_message = await self.ctx.interaction.original_message()
            embed.set_author(name="About", icon_url=original_message.author.display_avatar.url)

            await interaction.response.send_message(embed=embed, view=LegalView(ctx=self.ctx), ephemeral=True)

    @discord_button(label="Technical", style=ButtonStyle.gray)
    async def technical(self, button: Button, interaction: Interaction):
        class TechnicalView(EnhancedView):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.add_item(Button(label="Source Code", emoji="<:github:953746341413142638>",
                                     url="https://github.com/celsiusnarhwal/3515.games"))

        variables = {
            "Bot Version": toml.load("pyproject.toml")["tool"]["poetry"]["version"],
            "Python Version": platform.python_version(),
            "Pycord Version": discord.__version__,
            "Uptime": uptime.get_uptime(),
        }

        embed = discord.Embed(title="Technical", description="Statistics for nerds.", color=support.Color.mint())

        for index, (var, value) in enumerate(variables.items()):
            embed.add_field(name=var, value=value, inline=True)

            if index % 2 == 1:
                embed.add_field(name="\u200b", value="\u200b")

        original_message = await self.ctx.interaction.original_message()
        embed.set_author(name="About", icon_url=original_message.author.display_avatar.url)

        await interaction.response.send_message(embed=embed, view=TechnicalView(ctx=self.ctx), ephemeral=True)

    async def show_about(self):

        with support.Assets.about():
            about_text = open(os.path.join("pages", "main.md")).read()

        about_embed = discord.Embed(title="About Me", description=about_text,
                                    color=support.Color.mint())

        with support.Assets.about():
            bot_logo = discord.File("bot_logo.png", filename="bot_logo.png")
            about_embed.set_image(url="attachment://bot_logo.png")

            await self.ctx.respond(embed=about_embed, files=[bot_logo], view=self, ephemeral=True)
