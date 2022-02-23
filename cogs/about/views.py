import datetime
import json
import os
import textwrap

import discord
import toml
from discord import Interaction, ButtonStyle
from discord.ext import pages as discord_pages
from discord.ui import Button, button as discord_button

import support
from support.views import EnhancedView


class AboutView(EnhancedView):
    def __init__(self, **kwargs):
        super(AboutView, self).__init__(**kwargs)

    @discord_button(label="Third-Party Acknowledgements", style=ButtonStyle.gray)
    async def third_party_acknowledgements(self, button: Button, interaction: Interaction):
        class AcknowledgementsView(EnhancedView):
            def __init__(self, **kwargs):
                super(AcknowledgementsView, self).__init__()

            @discord_button(label="View Acknowledgements", style=ButtonStyle.gray)
            async def view_acknowledgements(self, button: Button, interaction: Interaction):
                licenses = json.load(open(os.path.join(os.getcwd(), "licenses.json")))

                pages = []
                for oss_license in licenses:
                    page_title = oss_license["Name"]
                    page_text = f"**{oss_license['License']}**\n\n{oss_license['LicenseText']}"

                    split_page_text = textwrap.wrap(page_text, 2000, break_long_words=False, replace_whitespace=False)

                    embeds = []
                    for index, text in enumerate(split_page_text):

                        if index == 1:
                            page_title += " (cont.)"

                        embeds.append(discord.Embed(title=page_title, description=text,
                                                    color=support.ExtendedColors.mint()))

                    pages.extend(embeds)

                paginator = discord_pages.Paginator(pages=pages, use_default_buttons=False,
                                                    custom_buttons=support.paginator_emoji_buttons())
                await paginator.respond(interaction, ephemeral=True)

        embed_text = "3515.games wouldn't be possible without the contributions of open-source software. " \
                     "Here, you'll find the required acknowledgements for the open-source software " \
                     "used by 3515.games. "

        tpa_prompt_embed = discord.Embed(title="Third-Party Acknowledgements", description=embed_text,
                                         color=support.ExtendedColors.mint())

        await interaction.response.send_message(embed=tpa_prompt_embed, view=AcknowledgementsView(), ephemeral=True)

    async def show_about(self):
        pyproject = toml.load(open(os.path.join(os.getcwd(), "pyproject.toml")))

        version = pyproject["tool"]["poetry"]["version"]
        copyright_year = datetime.datetime.now().year

        about_text = f"3515.games is a project of 3515 Productions, a one-man band led by <@170966436125212673>.\n" \
                     f"\n" \
                     f"© {copyright_year} 3515 Productions. All rights reserved.\n" \
                     f"\n" \
                     f"Thanks for playing!"

        about_embed = discord.Embed(title=f"3515.games v{version}", description=about_text,
                                    color=support.ExtendedColors.mint())
        about_embed.set_image(url="https://i.ibb.co/5jCMMRJ/3515-games-logo.png")

        await self.ctx.respond(embed=about_embed, view=self, ephemeral=True)
