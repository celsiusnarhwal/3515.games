from __future__ import annotations

import aiohttp
import discord
import inflect as ifl
from discord import Interaction, ButtonStyle
from discord.ui import Select, Button, button as discord_button

import support
from cogs import cah
from support import EnhancedView

inflect = ifl.engine()


class CAHTerminableView(EnhancedView):
    """
    A subclass of :class:`EnhancedView` whose views are set to automatically disabled themselves and stop
    listening for interactions upon the end of the turn of the player who created them.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        game: cah.CAHGame = cah.CAHGame.retrieve_game(self.ctx.channel_id)
        player: cah.CAHPlayer = game.retrieve_player(self.ctx.user)

        player.terminable_views.append(self)


class PackSelectView(EnhancedView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cards = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        pack_menu: Select = discord.utils.find(lambda x: isinstance(x, Select), self.children)

        for option in pack_menu.options:
            if option.value in pack_menu.values:
                option.default = True
            else:
                option.default = False

        await interaction.response.edit_message(view=self)

        return super().interaction_check(interaction)

    @discord_button(label="Create Game", style=ButtonStyle.green, row=1)
    async def submit(self, button: Button, interaction: Interaction):
        pack_menu: Select = discord.utils.find(lambda x: isinstance(x, Select), self.children)

        await interaction.edit_original_message(content="Creating your Cards Against Humanity game...",
                                                embed=None,
                                                view=None)

        packs = pack_menu.values or ["CAH Base Set"]

        request_url = "https://restagainsthumanity.com/api"

        async with aiohttp.ClientSession() as session:
            async with session.get(request_url, params={"packs": ",".join(packs)}) as response:
                if response.status == 200:
                    self.cards = await response.json()
                else:
                    msg = f"I couldn't communicate with [REST Against Humanity](https://restagainsthumanity.com), " \
                          f"my source for CAH card data. Please try again.\n" \
                          f"\n" \
                          f"If the problem persists, open an issue on [REST Against Humanity's GitHub page]" \
                          f"({support.github().get_repo('rest-against-humanity').html_url}/issues/new)."
                    embed = discord.Embed(title="Something went wrong.", description=msg, color=support.Color.red())
                    await interaction.edit_original_message(content=None, embed=embed, view=None)

                    return

        self.stop()

    async def get_packs(self):
        with support.Assets.cah():
            packs = open("packs.txt").read().splitlines()

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
                value=pack
            )

        self.add_item(pack_menu)

        msg = "Pick the packs you want to play with cards from. You can pick as many as you like, but you must pick " \
              "at least one.\n" \
              "\n" \
              "(Tip: When in doubt, the CAH Base Set is never a bad choice.)"
        embed = discord.Embed(title="Pack Selection", description=msg, color=support.Color.mint())

        embed.set_author(name="Cards Against Humanity", icon_url=self.ctx.me.display_avatar.url)

        await self.ctx.interaction.edit_original_message(embed=embed, view=self)

        await self.wait()

        return self.cards


class CAHCardSelectView(CAHTerminableView):
    def __init__(self, player: cah.CAHPlayer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player = player
        self.game = player.game
        self.cards = player.hand
        self.candidates: list[cah.CAHCandidateCard] = []
        self.submission: cah.CAHCandidateCard = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        menu: Select = discord.utils.find(lambda x: isinstance(x, Select), self.children)

        if not self.candidates:
            self.candidates = cah.CAHCandidateCard.make_candidates(self.player, *menu.values)

            if self.game.black_card.pick == 2:
                self.clear_items()

                option1_button = Button(label="Option 1", style=ButtonStyle.gray)
                option1_button.callback = self.order_option_1_callback
                self.add_item(option1_button)

                option2_button = Button(label="Option 2", style=ButtonStyle.gray)
                option2_button.callback = self.order_option_2_callback
                self.add_item(option2_button)

                msg = "Choose the order in which you want to play your selected cards."
                embed = discord.Embed(title="Card Order", description=msg, color=support.Color.mint())
                embed.set_author(name="Cards Against Humanity", icon_url=self.ctx.me.display_avatar.url)
                for i, option in enumerate(self.candidates):
                    embed.add_field(name=f"Option {i + 1}", value=option.text, inline=False)

                await interaction.response.defer()
                await self.ctx.interaction.edit_original_message(embed=embed, view=self)
            else:
                self.submission = self.candidates[0]
                await self.finish()

        return await super().interaction_check(interaction)

    def get_menu(self):
        menu = Select(
            placeholder=f"Pick {inflect.number_to_words(self.game.black_card.pick)} white "
                        f"{inflect.plural('card', self.game.black_card.pick)}",
            min_values=self.game.black_card.pick,
            max_values=self.game.black_card.pick,
        )

        for card in self.cards:
            menu.add_option(label=card, value=card)

        return menu

    async def order_option_1_callback(self, interaction: Interaction):
        self.submission = self.candidates[0]
        await self.finish()

    async def order_option_2_callback(self, interaction: Interaction):
        self.submission = self.candidates[1]
        await self.finish()

    async def finish(self):
        embed = discord.Embed(title=f"{inflect.plural('Card', self.game.black_card.pick)} Played!",
                              description="Please wait for the other players to finish.",
                              color=support.Color.mint())

        embed.add_field(name="Your Submission", value=self.submission.text, inline=False)

        embed.set_author(name="Cards Against Humanity", icon_url=self.ctx.me.display_avatar.url)
        await self.ctx.interaction.edit_original_message(embed=embed, view=None)

        self.stop()

    async def select_card(self):
        self.add_item(self.get_menu())

        msg = f"Select {inflect.number_to_words(self.game.black_card.pick)} white " \
              f"{inflect.plural('card', self.game.black_card.pick)} from the dropdown menu."

        embed = discord.Embed(title="Card Selection", description=msg, color=support.Color.mint())

        embed.add_field(name="Black Card", value=self.game.black_card.text)

        embed.set_author(name="Cards Against Humanity", icon_url=self.ctx.me.display_avatar.url)

        await self.ctx.respond(embed=embed, view=self, ephemeral=True)

        await self.wait()

        return self.submission


class CAHVotingView(CAHTerminableView):
    def __init__(self, game: cah.CAHGame, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = game
        self.selection: cah.CAHCandidateCard = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        menu: Select = discord.utils.find(lambda x: isinstance(x, Select), self.children)

        self.selection = discord.utils.find(lambda c: c.uuid == menu.values[0], self.game.candidates)

        self.stop()

    async def vote(self):
        menu = Select(
            placeholder="Pick a submission",
            min_values=1,
            max_values=1,
        )

        msg = "Pick your favorite submission. All submissions are anonymous; you won't know who submitted what " \
              "until you make your choice."

        if self.game.settings.use_czar:
            msg += " The player who made the submission you choose will recieve a point."
        else:
            msg += " You cannot vote for your own submission."

        embed = discord.Embed(title="Voting", description=msg, color=support.Color.mint())
        embed.set_author(name="Cards Against Humanity", icon_url=self.ctx.me.display_avatar.url)
        embed.add_field(name="Black Card", value=self.game.black_card.text)

        for i, candidate in enumerate([c for c in self.game.candidates if c.player.user != self.ctx.user]):
            menu.add_option(label=f"Submission {i + 1}", value=candidate.uuid)
            embed.add_field(name=f"Submission {i + 1}", value=candidate.text, inline=False)

        self.add_item(menu)

        await self.ctx.respond(embed=embed, view=self, ephemeral=True)

        await self.wait()

        embed = discord.Embed(title="Your Vote", description=self.selection.text, color=support.Color.mint())
        embed.set_author(name="Cards Against Humanity", icon_url=self.ctx.me.display_avatar.url)
        embed.add_field(name="Submitted By", value=f"{self.selection.player.user.mention}", inline=False)

        if not self.game.settings.use_czar:
            embed.fields[0].value = embed.fields[0].value + "\n\nPlease wait for the other players to finish."

        await self.ctx.interaction.edit_original_message(embed=embed, view=None)

        return self.selection


class CAHStatusCenterView(EnhancedView):
    def __init__(self, game: cah.CAHGame, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.game = game

    async def interaction_check(self, interaction: Interaction) -> bool:
        """
        Processes interactions with the CAH Status Center.

        :param interaction: The interaction.
        """
        # get the select menu
        status_menu: Select = discord.utils.find(lambda x: isinstance(x, Select), self.children)

        choice = status_menu.values[0]

        options = {
            "settings": self.settings(),
            "players": self.players(),
            "leaderboard": self.leaderboard(),
        }

        # get embed from the appropriate method based on the user's choice
        embed = options[choice]
        embed.set_author(name="CAH Status Center", icon_url=self.ctx.me.display_avatar.url)

        await interaction.response.edit_message(embed=embed)

        return super().interaction_check(interaction)

    async def open_status_center(self):
        """
        Sends the UNO Status Center menu in chat.
        """
        status_menu = self.get_menu()
        self.add_item(status_menu)

        msg = "Pick an item from the menu below and I'll tell you what you want to know."

        embed = discord.Embed(title="Welcome to the CAH Status Center!",
                              description=msg,
                              color=support.Color.mint())

        embed.set_author(name="Cards Against Humanity", icon_url=self.ctx.me.display_avatar.url)

        await self.ctx.respond(embed=embed, view=self, ephemeral=True)

    def get_menu(self) -> Select:
        menu = Select(placeholder="What do you want to know?",
                      min_values=1,
                      max_values=1)

        menu.add_option(label="Settings", value="settings", emoji="⚙️", description="See the settings for this game.")
        menu.add_option(label="Players", value="players", emoji="👥", description="See who's playing this game.")

        if not self.game.is_joinable:
            menu.add_option(label="Leaderboard", value="leaderboard", emoji="🏆", description="See the leaderboard.")

        return menu

    def settings(self):
        return discord.Embed(title="⚙️ Game Settings", description=self.game.settings, color=support.Color.mint())

    def players(self):
        embed = discord.Embed(title="Players", color=support.Color.mint())
        embed.add_field(name="Game Host", value=f"{self.game.host.name} ({self.game.host.mention})", inline=False)

        other_players = [p for p in self.game.players if p.user != self.game.host]
        embed.add_field(name="Other Players",
                        value="\n".join(f"— {player.user.name} ({player.user.mention})" for player in other_players),
                        inline=False)

        return embed

    def leaderboard(self):
        leaderboard = self.game.get_leaderboard()

        embed = discord.Embed(title="Leaderboard", color=support.Color.mint())

        for i, group in enumerate(leaderboard):
            if len(group) == 1:
                players = group[0].user.name
            else:
                players = ", ".join({player.user.name for player in group[:-1]})
                if group == leaderboard[-1] and len(group) > 3:
                    players += " & everyone else"
                else:
                    players += f" & {group[-1].user.name}"

                players += f"— {group[0].points} points"

            embed.add_field(name=f"{inflect.ordinal(i + 1)} Place", value=players, inline=False)

        return embed


class CAHVoiceURLView(EnhancedView):
    """
    Provides a URL button that points to a CAH game's associated voice channel.
    """

    def __init__(self, channel: discord.VoiceChannel, **kwargs):
        super().__init__(**kwargs)
        self.add_item(Button(label="Join voice channel", url=channel.jump_url))
