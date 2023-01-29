########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import discord
import inflect as ifl
from discord import Interaction, ButtonStyle
from discord.ui import Button, Select, button as discord_button
from llist import dllist

import support
from cogs import uno
from support.views import View, ConfirmationView

inflect = ifl.engine()


class UnoTerminableView(View):
    """
    A subclass of :class:`EnhancedView` whose views are set to automatically disable themselves and stop
    listening for interactions upon the end of the turn of the player who created them.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.game: uno.UnoGame = uno.UnoGame.retrieve_game(self.ctx.channel_id)
        self.player: uno.UnoPlayer = self.game.retrieve_player(self.ctx.user)
        self.turn_uuid: str = self.game.turn_uuid

        self.player.terminable_views.append(self)

    async def interaction_check(self, interaction: Interaction) -> bool:
        if self.game.turn_uuid == self.turn_uuid:
            return await super().interaction_check(interaction)
        else:
            embed = discord.Embed(
                title="Something went wrong.",
                description="Try doing that again.",
                color=support.Color.error(),
            )

            await interaction.response.edit_message(embed=embed, view=None)

    async def full_stop(self):
        self.stop()
        self.disable_all_items()
        await self.ctx.interaction.edit_original_response(view=self)


class UnoTerminableConfView(ConfirmationView, UnoTerminableView):
    """
    Combines the functionality of :class:`ConfirmationView` and :class:`UnoTerminableView` and does nothing else.
    """


class UnoCardSelectView(UnoTerminableView):
    """
    Provides an interface for a player to select a card to play.
    """

    class UnoCardSelectPaginator:
        def __init__(self, pages: dllist):
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
            pages=dllist(support.split_list(self.cards, 23))
        )

    async def interaction_check(self, interaction: Interaction) -> bool:
        """
        Proccesses the result of the player's interaction with the card selection menu.

        :param interaction: The interaction.
        """
        # get the card selection menu
        card_menu: Select = discord.utils.find(
            lambda x: isinstance(x, Select), self.children
        )

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
            played_card: uno.UnoCard = discord.utils.find(
                lambda x: x.uuid == selected_option, self.player.hand
            )

            # verify that the card is playable
            if not self.game.is_card_playable(played_card):
                msg = (
                    "You can only play a card that matches the color or suit of the last card played. "
                    "Pick a different card, or draw a card with `/uno play > Draw Card` if there are "
                    "no cards you can play."
                )
                embed = discord.Embed(
                    title="You can't play that card.",
                    description=msg,
                    color=support.Color.error(),
                )

                await interaction.response.send_message(embed=embed, ephemeral=True)
                card_menu.values.clear()
                await self.ctx.interaction.edit_original_response(view=self)
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
            pages=dllist(
                [self.cards[i : i + 23] for i in range(0, len(self.cards), 23)]
            )
        )

        msg = (
            f"Pick a card from the dropdown menu. You can play any card that matches the color or suit of the "
            f"last card played. You can also play a Wild or Wild +4 card, if you have one."
        )
        msg += (
            f"\n\n{self.game.last_move_str}"
            if self.game.last_move_str
            else "\n\nNo cards have been played during this round yet, so you can play any card in your hand."
        )

        embed = discord.Embed(
            title="Play a Card", description=msg, color=support.Color.mint()
        )

        card_menu = self.get_menu()
        filter_button = self.get_filter_button()

        self.clear_items()
        self.add_item(card_menu)
        self.add_item(filter_button)

        await interaction.response.edit_message(embed=embed, view=self)

    async def show_playable_cards(self, interaction: Interaction):
        """
        A callback for a button that switches the menu to only show cards that can played this round.
        """

        playable_cards = [
            card for card in self.cards if self.game.is_card_playable(card)
        ]
        if playable_cards:
            self.paginator = self.UnoCardSelectPaginator(
                pages=dllist(
                    [
                        playable_cards[i : i + 23]
                        for i in range(0, len(playable_cards), 23)
                    ]
                )
            )

            card_menu = self.get_menu()
            filter_button = self.get_filter_button()

            self.clear_items()
            self.add_item(card_menu)
            self.add_item(filter_button)

            await interaction.response.edit_message(view=self)
        else:
            msg = "You have no cards that can be played this turn. You must draw a card with `/uno play > Draw Card`."
            embed = discord.Embed(
                title="No Playable Cards", description=msg, color=support.Color.error()
            )

            filter_button = self.get_filter_button()
            self.clear_items()
            self.add_item(filter_button)

            await interaction.response.edit_message(embed=embed, view=self)

    def get_filter_button(self):
        if discord.utils.find(
            lambda x: isinstance(x, Button) and x.label == "Show Playable Cards",
            self.children,
        ):
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
            placeholder += (
                f" (Page {self.paginator.page_number} of {len(self.paginator.pages)})"
            )

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

        self.add_item(self.get_filter_button())

        msg = (
            f"Pick a card from the dropdown menu. You can play any card that matches the color or suit of the "
            f"last card played. You can also play a Wild or Wild Draw Four card, if you have one."
        )
        msg += (
            f"\n\n{self.game.last_move_str}"
            if self.game.last_move_str
            else "\n\nNo cards have been played during this round yet, so you can play any card in your hand."
        )

        embed = discord.Embed(
            title="Play a Card", description=msg, color=support.Color.mint()
        )
        await self.ctx.respond(embed=embed, view=self, ephemeral=True)

        await self.wait()

        if self.success:
            await self.ctx.interaction.edit_original_response(view=self)
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
        msg = (
            "You can either a) draw a card, or b) draw a card and, if possible, play it "
            "automatically. Note that Wild and Wild +4 cards will never be played automatically.\n"
            "\n"
            "Drawing a card will end your turn."
        )
        embed = discord.Embed(
            title="Draw a Card", description=msg, color=support.Color.mint()
        )
        await self.ctx.respond(embed=embed, view=self, ephemeral=True)

        await self.wait()

        if self.success:
            await self.ctx.interaction.edit_original_response(view=None)
        else:
            msg = "Okay! Make your move whenever you're ready."
            await self.ctx.interaction.edit_original_response(
                content=msg, embed=None, view=None
            )


class WildColorSelectView(UnoTerminableView):
    """
    Provides an interface for color selection when a Wild card is played.
    """

    def __init__(self, player: uno.UnoPlayer, card: uno.UnoCard, **kwargs):
        super().__init__(**kwargs)
        self.player = player
        self.game = player.game
        self.card = card

    @discord_button(label="Red", emoji="🔴", style=ButtonStyle.gray)
    async def red(self, button: Button, interaction: Interaction):
        self.card.transformation = uno.UnoCardColor.RED
        self.success = True
        self.stop()

    @discord_button(label="Blue", emoji="🔵", style=ButtonStyle.gray)
    async def blue(self, button: Button, interaction: Interaction):
        self.card.transformation = uno.UnoCardColor.BLUE
        self.success = True
        self.stop()

    @discord_button(label="Green", emoji="🟢", style=ButtonStyle.gray)
    async def green(self, button: Button, interaction: Interaction):
        self.card.transformation = uno.UnoCardColor.GREEN
        self.success = True
        self.stop()

    @discord_button(label="Yellow", emoji="🟡", style=ButtonStyle.gray)
    async def yellow(self, button: Button, interaction: Interaction):
        self.card.transformation = uno.UnoCardColor.YELLOW
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
        msg = (
            "Since you played a Wild card, you get to choose the next color in play. The next player will be "
            "able to play any card that matches the color you select (or a Wild card of their own, of course)."
        )

        embed = discord.Embed(
            title="Color Selection", description=msg, color=support.Color.mint()
        )

        await self.ctx.interaction.edit_original_response(embed=embed, view=self)

        await self.wait()

        if self.success:
            embed = discord.Embed(
                title="Color in Play Changed",
                description=f"You changed the color in play to "
                f"**{self.card.transformation}**.",
                color=self.card.transformation_embed_color,
            )
            await self.ctx.interaction.edit_original_response(embed=embed, view=None)

        elif self.success is False:
            msg = "Okay! You can select a different card with `/uno play > Play Card`."
            await self.ctx.interaction.edit_original_response(
                content=msg, embed=None, view=None
            )

        return self.card


class UnoStatusCenterView(View):
    """
    The UNO Status Center.
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

        Parameters
        ----------
        interaction : Interaction
        """
        # get the select menu
        status_menu: Select = discord.utils.find(
            lambda x: isinstance(x, Select), self.children
        )

        choice = status_menu.values[0]

        options = {
            "settings": self.game_settings(),
            "players": self.player_list(),
            "turn": await self.turn_order(),
            "leaderboard": self.leaderboard(),
            "last": self.last_turn(),
            "mystats": self.player_stats(),
        }

        # get embeds from the appropriate method based on the user's choice
        embeds = options[choice]
        embeds[0].set_author(
            name="UNO Status Center", icon_url=self.ctx.me.display_avatar.url
        )

        await interaction.response.edit_message(embeds=embeds)

        return super().interaction_check(interaction)

    def create_menu(self) -> Select:
        """
        Creates the UNO Status Center's menu.
        """
        status_menu = Select(
            placeholder="What do you want to know?", min_values=1, max_values=1
        )

        # these options are always available

        status_menu.add_option(
            label="Game Settings",
            value="settings",
            emoji="⚙️",
            description="See the settings for this game.",
        )

        status_menu.add_option(
            label="Players",
            value="players",
            emoji="👥",
            description="See who's playing in this game.",
        )

        # these options are only available after the game has started

        if not self.status.game.is_joinable:
            status_menu.add_option(
                label="Turn Order",
                value="turn",
                emoji="🕒",
                description="See the current turn order.",
            )

            status_menu.add_option(
                label="Leaderboard",
                value="leaderboard",
                emoji="🏆",
                description="See the leaderboard.",
            )

            status_menu.add_option(
                label="Last Turn",
                value="last",
                emoji="⏪",
                description="See what happened last turn.",
            )

            # these options are only available if the user is a player in the game

            if self.game.retrieve_player(self.invoker) is not None:
                status_menu.add_option(
                    label="Your Stats",
                    value="mystats",
                    emoji="📊",
                    description="See your personal game stats.",
                )

        return status_menu

    async def open_status_center(self):
        """
        Sends the UNO Status Center menu in chat.
        """
        status_menu = self.create_menu()
        self.add_item(status_menu)

        msg = (
            "Pick an item from the menu below and I'll tell you what you want to know."
        )

        embed = discord.Embed(
            title="Welcome to the UNO Status Center!",
            description=msg,
            color=support.Color.mint(),
        )

        embed.set_author(name="UNO", icon_url=self.ctx.me.display_avatar.url)

        await self.ctx.respond(embed=embed, view=self, ephemeral=True)

    def game_settings(self):
        """
        Returns an embed containing a string representation of the game settings.
        """
        settings = self.status.get_game_settings()

        embed = discord.Embed(
            title="⚙️ Game Settings", description=settings, color=support.Color.mint()
        )

        return [embed]

    def player_list(self):
        """
        Returns an embed containing a string representation of the player list.
        """
        players = self.status.get_player_list()

        embed = discord.Embed(title="👥 Players", color=support.Color.mint())

        embed.add_field(
            name="Game Host",
            value=f"{self.game.host.name} ({self.game.host.mention})",
        )

        embed.add_field(
            name="Players",
            value="\n".join(
                [f"- {player.name} ({player.mention})" for player in players]
            ),
        )

    async def turn_order(self):
        """
        Returns an embed containing a string representation of the turn order.
        """
        turn_order = await self.status.get_turn_order()

        embed = discord.Embed(title="🕒 Turn Order", color=support.Color.mint())

        current, following = turn_order[:2]

        embed.add_field(
            name="Now", value=f"{current.name} ({current.mention})", inline=False
        )
        embed.add_field(
            name="Next", value=f"{following.name} ({following.mention})", inline=False
        )

        if len(turn_order) > 2:
            embed.add_field(
                name="Later",
                value="\n".join(
                    [f"- {player.name} ({player.mention})" for player in turn_order[2:]]
                ),
                inline=False,
            )

        return [embed]

    def leaderboard(self):
        """
        Returns an embed containing a string representation of the leaderboard.
        """
        leaderboard = self.status.get_leaderboard()

        embed = discord.Embed(title="🏆 Leaderboard", color=support.Color.mint())

        if len(leaderboard) == 1:
            embed.add_field(name="1st Place", value="All Players")
        else:
            for index, group in enumerate(leaderboard):
                if leaderboard[index] == leaderboard[-1] and len(group) > 3:
                    group = [*group[:3], f"and {inflect.no('other', len(group) - 3)}"]

                embed.add_field(
                    name=f"{inflect.ordinal(index + 1)} Place",
                    value=inflect.join([player.name for player in group]),
                    inline=False,
                )

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
            embed.description = (
                "Nothing's happened this round yet. Check back once something happens."
            )

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


class UnoCalloutView(support.UserSelectionView, UnoTerminableView):
    def __init__(self, *args, **kwargs):
        kwargs.update(
            {
                "max_users": 1,
                "placeholder": "Who's the impostor?",
            }
        )

        super().__init__(*args, **kwargs)

        self.selected_player: uno.UnoPlayer = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        select: Select = discord.utils.find(
            lambda item: isinstance(item, Select), self.children
        )

        uno_game = uno.UnoGame.retrieve_game(self.ctx.channel_id)
        challenger: uno.UnoPlayer = uno_game.retrieve_player(self.ctx.user)
        target: uno.UnoPlayer = uno_game.retrieve_player(select.values[0])

        if not target:
            embed = discord.Embed(
                title="That's not a player.",
                description="You can only call out users who are also players in this UNO game.",
                color=support.Color.error(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await self.ctx.interaction.edit_original_response(view=self)
        elif challenger == target:
            embed = discord.Embed(
                title="Come on, man.",
                description="This should really go without saying, but you can't call out "
                "yourself. Choose another player to call out.",
                color=support.Color.error(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await self.ctx.interaction.edit_original_response(view=self)
        else:
            self.selected_player = target
            self.stop()
            return await super().interaction_check(interaction)

    async def present(self, *args, **kwargs) -> uno.UnoPlayer:
        msg = (
            'If you think a player has one card left and hasn\'t said "UNO!", you can call them out for it. '
            "If you're right, they'll draw two cards; if you're wrong, you'll draw one and forfeit your turn.\n"
            "\n"
            "Pick a player from the dropdown menu."
        )

        embed = discord.Embed(
            title="Make a Callout",
            description=msg,
            color=support.Color.mint(),
        )

        await self.ctx.respond(
            embed=embed,
            view=self,
            ephemeral=True,
        )

        await self.wait()
        return self.selected_player


class UnoKickPlayerView(support.UserSelectionView):
    def __init__(self, *args, **kwargs):
        kwargs.update(
            {
                "max_users": 1,
                "placeholder": "Select a player",
            }
        )

        super().__init__(*args, **kwargs)

        self.game = uno.UnoGame.retrieve_game(self.ctx.channel_id)
        self.selected_player: uno.UnoPlayer = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        select: Select = discord.utils.find(
            lambda item: isinstance(item, Select), self.children
        )

        player = self.game.retrieve_player(select.values[0])

        if not player:
            embed = discord.Embed(
                title="That's not a player.",
                description="You can only kick users who are also players in this UNO game.",
                color=support.Color.error(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif player == self.game.retrieve_player(self.ctx.user):
            embed = discord.Embed(
                title="You can't kick yourself.",
                description="You can't kick yourself from the game. If you want to leave, "
                "use `/uno ciao > Leave Game` (consider transferring your host powers to another player beforehand, "
                "though).",
                color=support.Color.error(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            self.selected_player = player
            self.stop()
            self.disable_all_items()
            await interaction.response.edit_message(view=self)
            return await super().interaction_check(interaction)

    async def present(self, *args, **kwargs):
        msg = "Select a player to kick.\n\n"

        if self.game.is_joinable:
            msg += (
                "Kicked players can rejoin the game at any time before it starts. Even if they don't rejoin, "
                "they can still spectate and chat in the game thread."
            )
        else:
            msg += "Kicked players can still spectate and chat in the game thread."

        embed = discord.Embed(
            title="Kick a Player",
            description=msg,
            color=support.Color.caution(),
        )

        await self.ctx.respond(
            embed=embed,
            view=self,
            ephemeral=True,
        )

        await self.wait()
        return self.selected_player


class UnoTransferHostView(support.UserSelectionView):
    def __init__(self, *args, **kwargs):
        kwargs.update(
            {
                "max_users": 1,
                "placeholder": "Select a player",
            }
        )

        super().__init__(*args, **kwargs)

        self.game = uno.UnoGame.retrieve_game(self.ctx.channel_id)
        self.selected_player: uno.UnoPlayer = None

    async def interaction_check(self, interaction: Interaction) -> bool:
        select: Select = discord.utils.find(
            lambda item: isinstance(item, Select), self.children
        )

        player = self.game.retrieve_player(select.values[0])

        if not player:
            embed = discord.Embed(
                title="That's not a player.",
                description="You can only transfer your powers to other players in this UNO game.",
                color=support.Color.error(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif player == self.game.retrieve_player(self.ctx.user):
            embed = discord.Embed(
                title="???",
                description="...you're the Game Host. Choose someone else. ",
                color=support.Color.error(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            self.selected_player = player
            self.stop()
            self.disable_all_items()
            await interaction.response.edit_message(view=self)
            return await super().interaction_check(interaction)

    async def present(self, *args, **kwargs):
        msg = "Select a player to make the new Game Host."
        embed = discord.Embed(
            title="Transfer Host Powers",
            description=msg,
            color=support.Color.caution(),
        )

        await self.ctx.respond(
            embed=embed,
            view=self,
            ephemeral=True,
        )

        await self.wait()
        return self.selected_player


class UnoGameEndView(View):
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
