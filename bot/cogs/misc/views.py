########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import platform
import re

import discord
import humanize
import inflect as ifl
import pendulum
from discord import ButtonStyle, Interaction
from discord.ui import Button
from discord.ui import button as discord_button
from yarl import URL

import clockworks
import shrine
import support
from cogs import uno
from support import BasePlayer, Gender, Pronoun
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
                label="Legal",
                emoji="🏛",
                url="https://3515.games/legal/",
                row=1,
            )
        )

        self.add_item(
            Button(
                label="Report a Bug",
                emoji="🐞",
                url="https://complain.3515.games",
                row=1,
            )
        )

        self.add_item(
            Button(
                label="celsiusnarhwal.dev",
                emoji=discord.PartialEmoji.from_str("<:celsius:535601639235518465>"),
                url="https://celsiusnarhwal.dev",
                row=2,
            )
        )

    @discord_button(label="Credits", emoji="🎬", style=ButtonStyle.gray)
    async def credits(self, _, interaction: Interaction):
        class CreditsView(View):
            @discord_button(label="Back", style=ButtonStyle.red)
            async def back(self, _, interaction: Interaction):
                await AboutView(ctx=self.ctx).present(interaction)

        with support.Assets.misc():
            embed = (
                discord.Embed(title="Credits", color=support.Color.mint())
                .add_field(
                    name="God Incarnate",
                    value=f"celsius narhwal ([@celsiusnarhwal](https://twitter.com/celsiusnarhwal))",
                    inline=False,
                )
                .add_field(
                    name="Super Cool Testers",
                    value="Frosty (Zander) ([@slyzander](https://twitter.com/slyzander))",
                    inline=False,
                )
                .add_field(name="Special Thanks", value="You, I suppose")
                .set_footer(
                    text=f"3515.games © {pendulum.now().year} celsius narhwal. Thank you kindly for your attention.",
                )
            )

            original_message = await self.ctx.interaction.original_response()
            embed.set_author(
                name="About", icon_url=original_message.author.display_avatar.url
            )

            await interaction.response.defer()
            await original_message.edit(
                embed=embed, attachments=[], view=CreditsView(ctx=self.ctx)
            )

    @discord_button(label="Technical Data", emoji="💻", style=ButtonStyle.gray, row=1)
    async def technical(self, _, interaction: Interaction):
        class TechnicalView(View):
            class TechnialDefinitionsView(View):
                @discord_button(label="Back", style=ButtonStyle.red)
                async def back(self, _, interaction: Interaction):
                    original_message = await self.ctx.interaction.original_response()
                    await interaction.response.defer()
                    await original_message.edit(
                        embed=embed, attachments=[], view=TechnicalView(ctx=self.ctx)
                    )

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

            @discord_button(label="Definitions", emoji="📖", style=ButtonStyle.gray)
            async def definitions(self, _, interaction: Interaction):
                embed = (
                    discord.Embed(
                        title="Technical Definitions", color=support.Color.mint()
                    )
                    .add_field(
                        name="Bot Version",
                        value="The current version of 3515.games.",
                        inline=False,
                    )
                    .add_field(
                        name="Python Version",
                        value="The current version of [Python](https://python.org) used by 3515.games.",
                        inline=False,
                    )
                    .add_field(
                        name="Pycord Version",
                        value="The current version of [Pycord](https://pycord.dev) used by 3515.games.",
                        inline=False,
                    )
                    .add_field(
                        name="Uptime",
                        value="The current length of time for which 3515.games has continuously been online.",
                        inline=False,
                    )
                    .add_field(
                        name="Ping",
                        value="An approximation of how long Discord is taking to respond to requests from 3515.games. "
                        "A high ping can cause 3515.games to appear slow or dysfunctional when responding to "
                        "user interactions.",
                        inline=False,
                    )
                    .set_author(
                        name="Technical Data",
                        icon_url=self.ctx.bot.user.display_avatar.url,
                    )
                )
                original_message = await self.ctx.interaction.original_response()
                await interaction.response.defer()
                await original_message.edit(
                    embed=embed,
                    attachments=[],
                    view=TechnicalView.TechnialDefinitionsView(ctx=self.ctx),
                )

        def get_latency():
            latency = self.ctx.bot.latency

            if latency >= 1:
                suffix = "second"
            else:
                latency *= 1000
                suffix = "m"

            return inflect.no(suffix, round(latency, 2))

        version = support.version()
        changelog = URL("https://3515.games/changelog").with_fragment(
            version.replace(".", "-")
        )

        statistics = {
            "Bot Version": f"{version} ([What's new?]({changelog}))",
            "Python Version": platform.python_version(),
            "Pycord Version": discord.__version__,
            "Uptime": re.sub(
                "an?", "1", humanize.naturaldelta(clockworks.clock().uptime)
            ),
            "Ping": get_latency(),
        }

        embed = discord.Embed(
            title="Technical Data",
            color=support.Color.mint(),
        )

        for index, (stat, value) in enumerate(statistics.items()):
            embed.add_field(name=stat, value=value, inline=True)

            if (index + 1) % 2 == 0:
                embed.add_field(**support.zero_width_field())

        original_message = await self.ctx.interaction.original_response()
        embed.set_author(
            name="About", icon_url=original_message.author.display_avatar.url
        )

        await interaction.response.defer()
        await original_message.edit(
            embed=embed, attachments=[], view=TechnicalView(ctx=self.ctx)
        )

    async def present(self, interaction: Interaction = None):
        with shrine.Torii.misc() as torii:
            template = torii.get_template("about.md")
            about_text = template.render()

        about_embed = discord.Embed(
            title="About Me", description=about_text, color=support.Color.mint()
        )

        with support.Assets.misc():
            if interaction:
                await interaction.response.defer()
                await interaction.edit_original_response(
                    embed=about_embed, attachments=[], view=self
                )
            else:
                await self.ctx.respond(embed=about_embed, view=self, ephemeral=True)


class HelpView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        def get_help_url(game: str):
            return f"https://3515.games/games/{game}/"

        self.add_item(
            Button(
                url=get_help_url("rps"),
                label="Rock-Paper-Scissors",
                emoji="🪨",
            )
        )

        self.add_item(
            Button(
                url=get_help_url("uno"),
                label="UNO",
                emoji=uno.UnoCard(uno.UnoCardColor.WILD).emoji,
            )
        )

        self.add_item(
            Button(
                url=get_help_url("chess"),
                label="Chess",
                emoji="♟️",
            )
        )

        self.add_item(
            Button(
                url=get_help_url("cah"),
                label="Cards Against Humanity",
                emoji="✏️",
            )
        )

    async def present(self, ctx: discord.ApplicationContext):
        await ctx.respond(content="Get help with what?", view=self, ephemeral=True)


class PronounsView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.add_item(
            Button(
                url="https://pronoundb.org/register",
                label="Create PronounDB Account",
            )
        )

        self.add_item(
            Button(
                url="https://pronoundb.org/me",
                label="View PronounDB Account",
            )
        )

        self.add_item(
            Button(
                url="https://3515.games/games/features/pronouns",
                label="Learn More",
            )
        )

    async def present(self, ctx: discord.ApplicationContext):
        player = BasePlayer(user=ctx.user)

        msg = (
            "You can choose the pronouns I use to refer to you by creating a [PronounDB](https://pronoundb.org) "
            "account and linking your Discord account to it. If you've already done that, you're good to go. "
            "Otherwise, you can get started with the buttons below.\n"
            "\n"
            "I'll try my best to refer to you with the pronouns you've set on PronounDB (or with they/them pronouns "
            "if you haven't set any)."
        )

        they, them, their = Pronoun.THEY, Pronoun.THEM, Pronoun.THEIR

        pronouns = inflect.join(
            [
                f"{they.transform(g)}/{(them.transform(g) if g is not Gender.NEUTER else their.transform(g))}"
                for g in player.genders
            ]
        )

        embed = discord.Embed(
            title="Pronouns", description=msg, color=support.Color.mint()
        ).set_footer(text=f"Your current pronouns are {pronouns}.")
        await ctx.respond(embed=embed, view=self, ephemeral=True)
