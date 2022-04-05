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


class AboutView(EnhancedView):
    def __init__(self, **kwargs):
        super(AboutView, self).__init__(**kwargs)
        self.add_item(Button(label="Source Code", emoji="<:github:953746341413142638>",
                             url="https://github.com/celsiusnarhwal/3515.games"))

    @discord_button(label="Acknowledgements", style=ButtonStyle.gray)
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
                                            color=support.Color.mint()))

            pages.extend(embeds)

        paginator = discord_pages.Paginator(pages=pages, use_default_buttons=False,
                                            custom_buttons=support.paginator_emoji_buttons())
        await paginator.respond(interaction, ephemeral=True)

    async def show_about(self):
        pyproject = toml.load(open(os.path.join(os.getcwd(), "pyproject.toml")))

        bot_version = pyproject["tool"]["poetry"]["version"]
        copyright_year = discord.utils.utcnow().year

        about_text = f"I'm 3515.games, a bot that lets you enjoy real-time social games with your friends on " \
                     f"Discord. Thanks for playing with me!\n" \
                     f"\n" \
                     f"(This is my about page. If you need help using me or playing any of my games, check out " \
                     f"`/help`.)\n" \
                     f"\n" \
                     f"__Technical Information__\n" \
                     f"Bot Version: {bot_version}\n" \
                     f"Python Version: {platform.python_version()}\n" \
                     f"Pycord Version: {discord.__version__}\n" \
                     f"\n" \
                     f"__Legal Information__\n" \
                     f"3515.games © {copyright_year} celsius narhwal. All rights reserved.\n" \
                     f"\n" \
                     f"UNO is a trademark of Mattel, Inc.\n" \
                     f"\n" \
                     f"*Cards Against Humanity* content is used under the " \
                     f"[Creative Commons BY-NC-SA 2.0](https://creativecommons.org/licenses/by-nc-sa/2.0/) license. " \
                     f"This software is in no way affiliated with or endorsed by Cards Against Humanity, LLC. " \
                     f"Cards Against Humanity is a trademark of Cards Against Humanity, LLC.\n" \
                     f"\n" \
                     f"3515.games makes use of open-source software. To view acknowledgements for this software, " \
                     f"select the 'Acknowledgements' button below."

        about_embed = discord.Embed(title="About Me", description=about_text,
                                    color=support.Color.mint())
        bot_logo = discord.File("bot_logo.png", filename="bot_logo.png")
        about_embed.set_image(url="attachment://bot_logo.png")

        await self.ctx.respond(embed=about_embed, file=bot_logo, view=self, ephemeral=True)
