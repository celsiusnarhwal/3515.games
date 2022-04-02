import discord
from discord import Interaction, ButtonStyle
from discord.ui import Button, Select, button as discord_button
from llist import dllist as DoublyLinkedList

import support
from cogs import uno
from support.views import EnhancedView, ConfirmationView


class GoToUnoThreadView(EnhancedView):
    def __init__(self, thread_url, **kwargs):
        super().__init__(**kwargs)
        self.add_item(Button(label="Go to game thread", url=thread_url))


class UnoTerminableView(EnhancedView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        game: uno.UnoGame = uno.UnoGame.retrieve_game(self.ctx.channel_id)
        player: uno.UnoPlayer = game.retrieve_player(self.ctx.user)

        player.terminable_views.append(self)


class UnoTerminableConfView(ConfirmationView, UnoTerminableView):
    pass


class UnoCardSelectView(UnoTerminableView):
    class UnoCardSelectPaginator:
        def __init__(self, pages: DoublyLinkedList):
            self.pages = pages
            self.current_page = self.pages.first
            self.page_number = 1

        def current(self):
            return self.current_page.value

        def previous(self):
            self.current_page = self.current_page.prev
            self.page_number -= 1
            return self.current()

        def next(self):
            self.current_page = self.current_page.next
            self.page_number += 1
            return self.current()

        def has_previous(self):
            return self.current_page.prev is not None

        def has_next(self):
            return self.current_page.next is not None

    def __init__(self, player: uno.UnoPlayer, cards: list[uno.UnoCard], **kwargs):
        super().__init__(**kwargs)
        self.player = player
        self.cards = cards

        self.game = self.player.game
        self.selected_card: uno.UnoCard = None
        self.paginator = self.UnoCardSelectPaginator(
            pages=DoublyLinkedList([self.cards[i:i + 23] for i in range(0, len(self.cards), 23)])
        )

    async def interaction_check(self, interaction: Interaction) -> bool:
        card_menu: Select = discord.utils.find(lambda x: isinstance(x, Select), self.children)

        if card_menu.values[0] in ["next", "prev"]:
            self.clear_items()
            if card_menu.values[0] == "next":
                self.paginator.next()
            elif card_menu.values[0] == "prev":
                self.paginator.previous()

            card_menu = await self.create_menu()
            self.add_item(card_menu)

            await interaction.response.edit_message(view=self)
        else:
            played_card: uno.UnoCard = discord.utils.find(lambda x: x.uuid == card_menu.values[0], self.player.hand)

            if not await self.game.is_card_playable(played_card):
                msg = "You can only play a card that matches the color or suit of the last card played. " \
                      "Pick a different card, or draw a card with `/uno draw` if there are no cards you can play."
                embed = discord.Embed(title="You can't play that card.", description=msg,
                                      color=support.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
            else:
                self.selected_card = played_card
                self.success = True
                await self.full_stop()
                return await super().interaction_check(interaction)

    async def create_menu(self) -> Select:
        placeholder = "Pick a card, any card!"

        if len(self.paginator.pages) > 1:
            placeholder += f" (Page {self.paginator.page_number} of {len(self.paginator.pages)})"

        card_menu = Select(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
        )

        for card in self.paginator.current():
            card_menu.add_option(label=str(card), emoji=card.emoji, value=card.uuid)

        if self.paginator.has_previous():
            card_menu.add_option(label="Previous Page", emoji="⏪", value="prev")
        if self.paginator.has_next():
            card_menu.add_option(label="Next Page", emoji="⏩", value="next")

        return card_menu

    async def select_card(self) -> dict:
        card_menu = await self.create_menu()
        self.add_item(card_menu)

        msg = f"Pick a card from the dropdown menu. You can play any card that matches the color or suit of the " \
              f"last card played. You can also play a Wild or Wild Draw Four card, if you have one."
        msg += f"\n\n{self.game.last_move}" if self.game.last_move else \
            "\n\nBecause no cards have been played during this round yet, you can play any card in your hand."
        msg += "\n\nYou can view all your cards with `/uno hand`."

        embed = discord.Embed(title="Play a Card", description=msg, color=support.Color.mint())
        await self.ctx.respond(embed=embed, view=self, ephemeral=True)

        await self.wait()

        if self.success:
            await self.ctx.interaction.edit_original_message(view=self)
            return self.selected_card
        else:
            return None


class WildColorSelectView(UnoTerminableView):
    def __init__(self, player: uno.UnoPlayer, **kwargs):
        super().__init__(**kwargs)
        self.player = player
        self.game = player.game

    @discord_button(label="Red", emoji="🔴", style=ButtonStyle.gray)
    async def red(self, button: Button, interaction: Interaction):
        self.game.color_in_play = "red"
        self.success = True
        self.stop()

    @discord_button(label="Blue", emoji="🔵", style=ButtonStyle.gray)
    async def blue(self, button: Button, interaction: Interaction):
        self.game.color_in_play = "blue"
        self.success = True
        self.stop()

    @discord_button(label="Green", emoji="🟢", style=ButtonStyle.gray)
    async def green(self, button: Button, interaction: Interaction):
        self.game.color_in_play = "green"
        self.success = True
        self.stop()

    @discord_button(label="Yellow", emoji="🟡", style=ButtonStyle.gray)
    async def yellow(self, button: Button, interaction: Interaction):
        self.game.color_in_play = "yellow"
        self.success = True
        self.stop()

    @discord_button(label="Cancel", style=ButtonStyle.red)
    async def cancel(self, button: Button, interaction: Interaction):
        self.success = False
        self.stop()

    async def choose_color(self):
        msg = "Since you played a Wild card, you get to choose the next color in play. The next player will be " \
              "able to play any card that matches the color you select (or a Wild card of their own, of course)."

        embed = discord.Embed(title="Color Selection", description=msg, color=support.Color.mint())

        await self.ctx.interaction.edit_original_message(embed=embed, view=self)

        await self.wait()

        if self.success:
            embed_colors = {
                "red": support.Color.brand_red(),
                "blue": support.Color.blue(),
                "green": support.Color.green(),
                "yellow": support.Color.yellow(),
            }

            embed = discord.Embed(title="Color in Play Changed",
                                  description=f"You changed the color in play to "
                                              f"**{self.game.color_in_play.title()}**.",
                                  color=embed_colors[self.game.color_in_play.casefold()])
            await self.ctx.interaction.edit_original_message(embed=embed, view=None)

        elif self.success is False:
            msg = "Okay! You can select a different card with `/uno play`."
            # await prompt.edit(content=msg, embed=None, view=None)
            await self.ctx.interaction.edit_original_message(content=msg, embed=None, view=None)
        return self.success


class UnoStatusCenterView(EnhancedView):
    def __init__(self, game: uno.UnoGame, **kwargs):
        super().__init__(**kwargs)
        self.game = game
        self.status = game.status

        if self.ctx is not None:
            self.invoker = self.ctx.user

    async def interaction_check(self, interaction: Interaction) -> bool:
        status_menu: Select = discord.utils.find(lambda x: isinstance(x, Select), self.children)

        choice = status_menu.values[0]

        options = {
            "settings": self.game_settings(),
            "players": self.player_list(),
            "turn": self.turn_order(),
            "leaderboard": self.leaderboard(),
            "last": self.last_turn(),
            "mystats": self.player_stats(),
        }

        embeds = options[choice]
        embeds[0].set_author(name="UNO Status Center", icon_url=self.ctx.me.display_avatar.url)

        await interaction.response.edit_message(embeds=embeds)

        return super().interaction_check(interaction)

    def create_menu(self) -> Select:
        status_menu = Select(placeholder="What do you want to know?",
                             min_values=1,
                             max_values=1)

        # pre-start options

        status_menu.add_option(label="Game Settings", value="settings", emoji="⚙️",
                               description="See the settings for this game.")

        status_menu.add_option(label="Players", value="players", emoji="👥",
                               description="See who's playing in this game.")

        # post-start options

        if not self.status.game.is_joinable:
            status_menu.add_option(label="Turn Order", value="turn", emoji="🕒",
                                   description="See the current turn order.")

            status_menu.add_option(label="Leaderboard", value="leaderboard", emoji="🏆",
                                   description="See the leaderboard.")

            status_menu.add_option(label="Last Turn", value="last", emoji="⏪",
                                   description="See what happened last turn.")

            # player-exclusive options

            if self.game.retrieve_player(self.invoker) is not None:
                status_menu.add_option(label="Your Stats", value="mystats", emoji="📊",
                                       description="See your personal game stats.")

        return status_menu

    async def open_status_center(self):
        status_menu = self.create_menu()
        self.add_item(status_menu)

        msg = "Pick an item from the menu below, and I'll to tell you what you want to know."

        if self.status.game.is_joinable:
            msg += "\n\nThis game hasn't started yet, so the information I can tell you is limited. To access all of " \
                   "my knowledge, you'll need to wait until the game starts."

        embed = discord.Embed(title="Welcome to the UNO Status Center!",
                              description=msg,
                              color=support.Color.mint())

        embed.set_author(name="UNO Status Center", icon_url=self.ctx.me.display_avatar.url)

        await self.ctx.respond(embed=embed, view=self, ephemeral=True)

    def game_settings(self):
        settings = self.status.get_game_settings()

        embed = discord.Embed(title="Game Settings", description=settings, color=support.Color.mint())

        return [embed]

    def player_list(self):
        players = self.status.get_player_list()

        def string_builder(player: uno.UnoPlayer):
            string = "— "

            if self.status.game.host == player.user:
                string += "👑 "

            string += f"{player.user.name} ({player.user.mention})"

            return string

        msg = "\n".join(string_builder(player) for player in players)

        msg += "\n\n(👑 = Game Host)"

        embed = discord.Embed(title="Players", description=msg, color=support.Color.mint())

        return [embed]

    def turn_order(self):
        turn_order = self.status.get_turn_order()

        def string_builder(index: int, player: uno.UnoPlayer):
            string = f"{index + 1}. "

            if not string.startswith(" "):
                string += f" {player.user.name}"
            else:
                string += f"{player.user.name}"

            if self.status.game.retrieve_player(player.user, return_node=True) == self.status.game.current_player:
                string = f"**{string}**"

            string += f" ({player.user.mention})"

            return string

        msg = "\n".join(string_builder(index, player) for index, player in enumerate(turn_order)) + "\n"

        embed = discord.Embed(title="Turn Order", description=msg, color=support.Color.mint())

        return [embed]

    def leaderboard(self):
        leaderboard = self.status.get_leaderboard()

        string = ""

        # if all players are tied, don't even bother iterating
        if len(leaderboard) == 1:
            string += f"1. All Players — {leaderboard[0][0].points} points"
        else:
            for index, group in enumerate(leaderboard):

                # handles special notation for players who are in or tied for last place
                if group == leaderboard[-1]:

                    # if there's only one player in last place, just print their name
                    if len(group) == 1:
                        string += f"{index + 1}. {group[0].user.name}"

                    # if there are multiple but less than four players in last place, print all of their names
                    elif len(group) <= 3:
                        string += "&".join(
                            f"{index + 1}. {', '.join(player.user.name for player in group)}".rsplit(",", 1)
                        )

                    # if there are four or more players in last place, print the first player's name + "everyone else"
                    else:
                        string += f"{index + 1}. {group[0].user.name} & everyone else"

                    string += f" — {group[0].points} points"
                else:
                    string += "&".join(
                        f"{index + 1}. {', '.join(player.user.name for player in group)}".rsplit(",", 1)
                    ) + f" — {group[0].points} points"

                string += "\n"

        embed = discord.Embed(title="Leaderboard", description=string, color=support.Color.mint())

        return [embed]

    def last_turn(self):
        embed = discord.Embed(title="Last Turn",
                              color=support.Color.mint())

        turn_record = self.status.get_last_turn()

        if turn_record:
            embed.description = "Here's what happened last turn:"
        else:
            embed.description = "Nothing's happened this round yet. Check back once something happens."

        return [embed] + self.status.get_last_turn()

    def player_stats(self):
        player = self.game.retrieve_player(self.invoker)
        embed = discord.Embed(title="Your Stats", color=support.Color.mint())
        embed.set_thumbnail(url=player.user.display_avatar.url)

        stats = self.status.get_player_stats(player)

        for stat, value in stats.items():
            embed.add_field(name=stat, value=value, inline=True)

            index = list(stats.keys()).index(stat)
            if (index + 1) % 2 == 0:
                embed.add_field(name="\u200b", value="\u200b")

        return [embed]


class UnoGameEndView(EnhancedView):
    def __init__(self, game: uno.UnoGame, **kwargs):
        super().__init__(**kwargs)
        self.game = game

    @discord_button(label="Leaderboard", emoji="🏆", style=ButtonStyle.secondary)
    async def leaderboard(self, button: Button, interaction: Interaction):
        leaderboard_embed = UnoStatusCenterView(game=self.game).leaderboard()[0]

        await interaction.response.send_message(embed=leaderboard_embed, ephemeral=True)
