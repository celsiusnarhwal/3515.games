from __future__ import annotations

import discord
from discord import Interaction, ButtonStyle
from discord.ui import Button, Select, button as discord_button
from llist import dllist as DoublyLinkedList

import support
from cogs import uno
from support.views import EnhancedView, ConfirmationView


class UnoTerminableView(EnhancedView):
    """
    A subclass of :class:`EnhancedView` whose views are set to automatically disabled themselves and stop
    listening for interactions upon the end of the turn of the player who created them.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        game: uno.UnoGame = uno.UnoGame.retrieve_game(self.ctx.channel_id)
        player: uno.UnoPlayer = game.retrieve_player(self.ctx.user)

        player.terminable_views.append(self)


class UnoTerminableConfView(ConfirmationView, UnoTerminableView):
    """
    A subclass of :class:`support.views.ConfirmationView` and :class:`UnoTerminableView` whose sole purpose is to
    inherit the functionality of both of those classes, giving :class:`ConfirmationView` objects the auto-terminating
    properties of :class:`UnoTerminableView` objects.
    """
    pass


class UnoCardSelectView(UnoTerminableView):
    """
    Provides an interface for a player to select a card to play.
    """

    class UnoCardSelectPaginator:
        """
        If the player who invokes :class:`UnoCardSelectView` has more than 23 cards in their hand, this class
        will paginate the selection menu into multiple pages with up to 23 cards each. 23 is chosen as the limit because
        Discord's select menus only allow for up to 25 items per page; for a player in an UNO game, that will be 23
        cards plus the next and previous page buttons.
        """

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
            pages=DoublyLinkedList(support.split_list(self.cards, 23))
        )

    async def interaction_check(self, interaction: Interaction) -> bool:
        """
        Proccesses the result of the player's interaction with the card selection menu.

        :param interaction: The interaction.
        """
        # get the card selection menu
        card_menu: Select = discord.utils.find(lambda x: isinstance(x, Select), self.children)

        # if there's no card menu, assume the user clicked a button and return the super call
        if not card_menu:
            return super().interaction_check(interaction)

        # get the selected option
        selected_option = card_menu.values[0:1]

        # if there's no selected option, assume the user clicked a button and return the super call
        if not selected_option:
            return await super().interaction_check(interaction)
        else:
            selected_option = selected_option[0]

        # if the selected option is the next or previous page buttons, switch pages accordingly
        if selected_option in ["next", "prev"]:
            button = discord.utils.find(lambda x: isinstance(x, Button), self.children)
            self.clear_items()
            if selected_option == "next":
                self.paginator.next()
            elif selected_option == "prev":
                self.paginator.previous()

            # once the page has been switched, recreate the selection menu with the cards on the new page
            card_menu = self.get_menu()
            self.add_item(card_menu)
            self.add_item(button)

            await interaction.response.edit_message(view=self)
        else:
            # if the selected option is a card, find the card with the corresponding UUID in the player's hand
            played_card: uno.UnoCard = discord.utils.find(lambda x: x.uuid == selected_option, self.player.hand)

            # verify that the card is playable
            if not self.game.is_card_playable(played_card):
                msg = "You can only play a card that matches the color or suit of the last card played. " \
                      "Pick a different card, or draw a card with `/uno draw` if there are no cards you can play."
                embed = discord.Embed(title="You can't play that card.", description=msg,
                                      color=support.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                card_menu.values.clear()
                await self.ctx.interaction.edit_original_message(view=self)
            else:
                # if it's playable, validate the interaction and stop the view
                self.selected_card = played_card
                self.success = True
                await interaction.response.defer()
                await self.full_stop()
                return await super().interaction_check(interaction)

    async def show_all_cards(self, interaction: Interaction):
        """
        A callback for a button that switches the menu to show all cards in the player's hand.
        """
        self.paginator = self.UnoCardSelectPaginator(
            pages=DoublyLinkedList([self.cards[i:i + 23] for i in range(0, len(self.cards), 23)])
        )

        msg = f"Pick a card from the dropdown menu. You can play any card that matches the color or suit of the " \
              f"last card played. You can also play a Wild or Wild Draw Four card, if you have one."
        msg += f"\n\n{self.game.last_move}" if self.game.last_move else \
            "\n\nNo cards have been played during this round yet, so you can play any card in your hand."

        embed = discord.Embed(title="Play a Card", description=msg, color=support.Color.mint())

        card_menu = self.get_menu()
        button = self.get_button()

        self.clear_items()
        self.add_item(card_menu)
        self.add_item(button)

        await interaction.response.edit_message(embed=embed, view=self)

    async def show_playable_cards(self, interaction: Interaction):
        """
        A callback for a button that switches the menu to only show cards that can played this round.
        """

        playable_cards = [card for card in self.cards if self.game.is_card_playable(card)]
        if playable_cards:
            self.paginator = self.UnoCardSelectPaginator(
                pages=DoublyLinkedList([playable_cards[i:i + 23] for i in range(0, len(playable_cards), 23)])
            )

            card_menu = self.get_menu()
            button = self.get_button()

            self.clear_items()
            self.add_item(card_menu)
            self.add_item(button)

            await interaction.response.edit_message(view=self)
        else:
            msg = "You have no cards that can be played this turn. You must draw a card with `/uno draw`."
            embed = discord.Embed(title="No Playable Cards", description=msg,
                                  color=support.Color.red())

            button = self.get_button()
            self.clear_items()
            self.add_item(button)

            await interaction.response.edit_message(embed=embed, view=self)

    def get_button(self):
        if discord.utils.find(lambda x: isinstance(x, Button) and x.label == "Show Playable Cards", self.children):
            button = Button(label="Show All Cards", style=ButtonStyle.secondary)
            button.callback = self.show_all_cards
            return button
        else:
            button = Button(label="Show Playable Cards", style=ButtonStyle.secondary)
            button.callback = self.show_playable_cards
            return button

    def get_menu(self) -> Select:
        """
        Creates the card selection menu.
        """
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
        """
        Sends the card selection menu and an accompanying message to the player in chat.
        """
        card_menu = self.get_menu()
        self.add_item(card_menu)

        self.add_item(self.get_button())

        msg = f"Pick a card from the dropdown menu. You can play any card that matches the color or suit of the " \
              f"last card played. You can also play a Wild or Wild Draw Four card, if you have one."
        msg += f"\n\n{self.game.last_move}" if self.game.last_move else \
            "\n\nNo cards have been played during this round yet, so you can play any card in your hand."

        embed = discord.Embed(title="Play a Card", description=msg, color=support.Color.mint())
        await self.ctx.respond(embed=embed, view=self, ephemeral=True)

        await self.wait()

        if self.success:
            await self.ctx.interaction.edit_original_message(view=self)
            return self.selected_card
        else:
            return None


class UnoDrawCardView(UnoTerminableView):
    """
    Provides an interface for drawing a card.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.autoplay = False

    @discord_button(label="Draw", style=ButtonStyle.green)
    async def draw(self, button: Button, interaction: Interaction):
        self.success = True
        self.autoplay = False
        self.stop()

    @discord_button(label="Draw and Play", style=ButtonStyle.green)
    async def draw_autoplay(self, button: Button, interaction: Interaction):
        self.success = True
        self.autoplay = True
        self.stop()

    @discord_button(label="Cancel", style=ButtonStyle.red)
    async def cancel(self, button: Button, interaction: Interaction):
        self.success = False
        self.stop()

    async def draw_card(self):
        """
        Sends the draw card menu and an accompanying message to the player in chat.
        """
        msg = "You can choose to either a) draw a card normally, or b) draw a card and, if possible, play it " \
              "automatically. Note that Wild and Wild Draw Four cards will never be played automatically.\n" \
              "\n" \
              "Drawing a card will end your turn."
        embed = discord.Embed(title="Draw a Card", description=msg, color=support.Color.mint())
        await self.ctx.respond(embed=embed, view=self, ephemeral=True)

        await self.wait()

        if self.success:
            await self.ctx.interaction.edit_original_message(view=None)
        else:
            msg = "Okay! Make your move whenever you're ready."
            await self.ctx.interaction.edit_original_message(content=msg, embed=None, view=None)


class WildColorSelectView(UnoTerminableView):
    """
    Provides an interface for color selection when a Wild card is played.
    """

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
        """
        Sends the color selection menu and an accompanying message to the player in chat.
        """
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
    """
    The frontend for the UNO Status Center. (The backend is :class:`uno.UnoStatusCenter`.)
    """

    def __init__(self, game: uno.UnoGame, **kwargs):
        super().__init__(**kwargs)
        self.game = game
        self.status = game.status

        if self.ctx is not None:
            self.invoker = self.ctx.user

    async def interaction_check(self, interaction: Interaction) -> bool:
        """
        Processes interactions with the UNO Status Center.

        :param interaction: The interaction.
        """
        # get the select menu
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

        # get embeds from the appropriate method based on the user's choice
        embeds = options[choice]
        embeds[0].set_author(name="UNO Status Center", icon_url=self.ctx.me.display_avatar.url)

        await interaction.response.edit_message(embeds=embeds)

        return super().interaction_check(interaction)

    def create_menu(self) -> Select:
        """
        Creates the UNO Status Center's menu.
        """
        status_menu = Select(placeholder="What do you want to know?",
                             min_values=1,
                             max_values=1)

        # these options are always available

        status_menu.add_option(label="Game Settings", value="settings", emoji="⚙️",
                               description="See the settings for this game.")

        status_menu.add_option(label="Players", value="players", emoji="👥",
                               description="See who's playing in this game.")

        # these options are only available after the game has started

        if not self.status.game.is_joinable:
            status_menu.add_option(label="Turn Order", value="turn", emoji="🕒",
                                   description="See the current turn order.")

            status_menu.add_option(label="Leaderboard", value="leaderboard", emoji="🏆",
                                   description="See the leaderboard.")

            status_menu.add_option(label="Last Turn", value="last", emoji="⏪",
                                   description="See what happened last turn.")

            # this option is only available if the user is a player in the game

            if self.game.retrieve_player(self.invoker) is not None:
                status_menu.add_option(label="Your Stats", value="mystats", emoji="📊",
                                       description="See your personal game stats.")

        return status_menu

    async def open_status_center(self):
        """
        Sends the UNO Status Center menu in chat.
        """
        status_menu = self.create_menu()
        self.add_item(status_menu)

        msg = "Pick an item from the menu below and I'll tell you what you want to know."

        embed = discord.Embed(title="Welcome to the UNO Status Center!",
                              description=msg,
                              color=support.Color.mint())

        embed.set_author(name="UNO", icon_url=self.ctx.me.display_avatar.url)

        await self.ctx.respond(embed=embed, view=self, ephemeral=True)

    def game_settings(self):
        """
        Returns an embed containing a string representation of the game settings.
        """
        settings = self.status.get_game_settings()

        embed = discord.Embed(title="⚙️ Game Settings", description=settings, color=support.Color.mint())

        return [embed]

    def player_list(self):
        """
        Returns an embed containing a string representation of the player list.
        """
        players = self.status.get_player_list()

        def string_builder(player: uno.UnoPlayer):
            string = "— "

            if self.status.game.host == player.user:
                string += "👑 "

            string += f"{player.user.name} ({player.user.mention})"

            return string

        msg = "\n".join(string_builder(player) for player in players)

        msg += "\n\n(👑 = Game Host)"

        embed = discord.Embed(title="👥 Players", description=msg, color=support.Color.mint())

        return [embed]

    def turn_order(self):
        """
        Returns an embed containing a string representation of the turn order.
        """
        turn_order = self.status.get_turn_order()

        def string_builder(index: int, player: uno.UnoPlayer):
            string = f"{index + 1}. "

            if not string.startswith(" "):
                string += f" {player.user.name}"
            else:
                string += f"{player.user.name}"

            if self.status.game.retrieve_player(player.user, return_node=True) == self.status.game.card_czar:
                string = f"**{string}**"

            string += f" ({player.user.mention})"

            return string

        msg = "\n".join(string_builder(index, player) for index, player in enumerate(turn_order)) + "\n"

        embed = discord.Embed(title="🕒 Turn Order", description=msg, color=support.Color.mint())

        return [embed]

    def leaderboard(self):
        """
        Returns an embed containing a string representation of the leaderboard.
        """
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
                        string += ", & ".join(
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

        embed = discord.Embed(title="🏆 Leaderboard", description=string, color=support.Color.mint())

        return [embed]

    def last_turn(self):
        """
        Returns a lists of embeds representing the events of the previous turn.
        """
        embed = discord.Embed(title="⏪ Last Turn", color=support.Color.mint())

        turn_record = self.status.get_last_turn()

        if turn_record:
            embed.description = "Here's what happened last turn:"
        else:
            embed.description = "Nothing's happened this round yet. Check back once something happens."

        return [embed] + self.status.get_last_turn()

    def player_stats(self):
        """
        Returns an embed containing the player's stats.
        """
        player = self.game.retrieve_player(self.invoker)
        embed = discord.Embed(title="📊 Your Stats", color=support.Color.mint())
        embed.set_thumbnail(url=player.user.display_avatar.url)

        stats = self.status.get_player_stats(player)

        for index, (stat, value) in enumerate(stats.items()):
            embed.add_field(name=stat, value=value, inline=True)

            if (index + 1) % 2 == 0:
                embed.add_field(name="\u200b", value="\u200b")

        return [embed]


class UnoGameEndView(EnhancedView):
    """
    When an UNO game ends, this view provides a button for players to see the final leaderboard. Since a thread
    ceases to be an UNO game thread when its associated game ends, the `/uno status` command will no longer work,
    so this view will be the only way to see the leaderboard.
    """

    def __init__(self, game: uno.UnoGame, **kwargs):
        super().__init__(**kwargs)
        self.game = game

    @discord_button(label="Leaderboard", emoji="🏆", style=ButtonStyle.secondary)
    async def leaderboard(self, button: Button, interaction: Interaction):
        leaderboard_embed = UnoStatusCenterView(game=self.game).leaderboard()[0]

        await interaction.response.send_message(embed=leaderboard_embed, ephemeral=True)
