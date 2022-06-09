from __future__ import annotations

import urllib.parse

import aiohttp
import discord
from discord import Interaction, ButtonStyle, SelectOption
from discord.ui import Select, Button, button as discord_button

import support
from support import EnhancedView


class PackSelectView(EnhancedView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cards = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        pack_menu: Select = discord.utils.find(lambda x: isinstance(x, Select), self.children)
        submit_button: Button = discord.utils.find(lambda x: isinstance(x, Button), self.children)

        submit_button.disabled = False
        for option in pack_menu.options:
            if option.value in pack_menu.values:
                option.default = True
            else:
                option.default = False

        await interaction.response.edit_message(view=self)

        return super().interaction_check(interaction)

    @discord_button(label="Create Game", style=ButtonStyle.green, row=1)
    async def submit(self, button: Button, interaction: Interaction):
        await interaction.edit_original_message(content="Creating your Cards Against Humanity game...",
                                                embed=None,
                                                view=None)

        pack_menu: Select = discord.utils.find(lambda x: isinstance(x, Select), self.children)

        try:
            packs = pack_menu.values
        except AttributeError:
            packs = ["CAH Base Set"]

        request_url = f"https://restagainsthumanity.com/api?packs={urllib.parse.quote(','.join(packs))}"

        async with aiohttp.ClientSession() as session:
            async with session.get(request_url) as response:
                if response.status == 200:
                    self.cards = await response.json()
                    pass

        self.stop()

    async def get_packs(self):
        packs = ["CAH: First Expansion",
                 "CAH: Second Expansion",
                 "CAH: Third Expansion",
                 "CAH: Fourth Expansion",
                 "CAH: Fifth Expansion",
                 "CAH: Sixth Expansion",
                 "CAH: Box Expansion",
                 "CAH: Blue Box Expansion",
                 "CAH: Green Box Expansion",
                 "CAH: Family Edition",
                 "CAH: College Pack",
                 "CAH: 2000s Nostalgia Pack",
                 "CAH: Procedurally-Generated Cards",
                 "Cards Against Humanity Saves America Pack",
                 "Absurd Box Expansion",
                 "Fantasy Pack",
                 "World Wide Web Pack",
                 "Geek Pack",
                 "Period Pack",
                 "Theatre Pack",
                 "Pride Pack",
                 "Weed Pack",
                 "Food Pack",
                 "Sci-Fi Pack"]

        pack_menu = Select(
            placeholder="Pick some packs",
            min_values=1,
            max_values=25,
            row=0,
        )

        pack_menu.add_option(label="CAH Base Set", value="CAH Base Set", default=True)

        for pack in packs:
            pack_menu.add_option(
                label=pack,
                value=pack + (" (Free Print & Play Public Beta)" if pack == "CAH: Family Edition" else '')
            )

        self.add_item(pack_menu)

        msg = "Pick the packs you want to play with cards from. You can pick as many as you like, but you must pick " \
              "at least one."
        embed = discord.Embed(title="Pack Selection", description=msg, color=support.Color.mint())
        await self.ctx.interaction.edit_original_message(embed=embed, view=self)

        await self.wait()

        return self.cards
