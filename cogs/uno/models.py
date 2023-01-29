########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import asyncio
import random
import string
import typing as t
import uuid
from enum import Enum, EnumMeta

import discord
import inflect as ifl
import tomlkit as toml
from discord.ext import pages as discord_pages
from llist import dllistnode, dllist
from pydantic import BaseSettings
from sortedcontainers import SortedKeyList

import shrine
import support
from cogs import uno
from shrine.kami import posessive
from support import HostedMultiplayerGame, BasePlayer

inflect = ifl.engine()


class UnoGame(HostedMultiplayerGame):
    """
    An UNO game.

    Parameters
    ----------
    settings : UnoGameSettings
        The game's settings.
    guild : discord.Guild
        The server (a.k.a. "guild") in which the game is taking place.
    thread : discord.Thread
        The game's associated thread.
    host : discord.Member
        The user who is the Game Host.
    """

    name = "UNO"

    def __init__(self, settings: UnoGameSettings, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings: UnoGameSettings = settings

        self.players = dllist()
        self.is_joinable: bool = True
        self.current_round: int = 0
        self.current_player = dllistnode()
        self.skip_next_player = False
        self.reverse_turn_order = False
        self.turn_uuid = None
        self.card_in_play: UnoCard = None
        self.turn_record = []
        self.processor = UnoEventProcessor(self)
        self.status = UnoStatusTracker(self)

        self.__all_games__[self.thread.id] = self

    @property
    def last_move_str(self):
        """
        A string describing the last card played. In the case of a Wild card, this also describes the color in play.
        """
        if self.card_in_play:
            last_move = f"The last card played was a **{self.card_in_play}**."

            if self.card_in_play.color is UnoCardColor.WILD:
                last_move += (
                    f" The color in play is **{self.card_in_play.transformation}**."
                )

            return last_move
        else:
            return ""

    async def game_timer(self):
        """
        Imposes an eight-hour time limit within which an UNO game must be completed.
        """
        await asyncio.sleep(60**2 * 8)

        if self.retrieve_game(self.thread.id):
            await self.force_close(reason="time_limit")

    def retrieve_player(
        self, user: discord.Member, *, return_node=False
    ) -> UnoPlayer | dllistnode:
        """
        Retrieve a player from the game given their corresponding :class:`discord.Member` object.

        Parameters
        ----------
        user : discord.Member

        return_node : bool
            Whether to return the player's :class:`llist.dllistnode` object rather than their :class:`UnoPlayer` object.

        Returns
        -------
        UnoPlayer | llist.dllistnode
            The player's :class:`UnoPlayer` object, or their :class:`llist.dllistnode`
            object if ``return_node`` is True.
        """

        if return_node:
            return discord.utils.find(
                lambda node: node.value.user.id == user.id, self.players.iternodes()
            )
        else:
            return discord.utils.find(
                lambda player: player.user.id == user.id, self.players.itervalues()
            )

    async def force_close(self, reason):
        if self.voice_channel:
            await self.voice_channel.delete()

        await super().force_close(reason)

    async def open_lobby(self):
        """
        Sends an introductory message at the creation of an UNO game thread and pins said message to that thread.
        """
        with shrine.Torii.uno() as torii:
            template = torii.get_template("lobby-open.md")
            intro_message = template.render(host=self.host.mention)

        intro_embed = discord.Embed(
            title=f"Welcome to {posessive(self.host.name)} UNO game!",
            description=intro_message,
            color=support.Color.mint(),
        )

        settings_embed = discord.Embed(
            title="Game Settings",
            description=str(self.settings),
            color=support.Color.mint(),
        )

        self.lobby_intro_msg = await self.thread.send(
            embeds=[intro_embed, settings_embed]
        )
        await self.lobby_intro_msg.pin()

    async def start_game(self):
        """
        Start an UNO game.
        """
        self.is_joinable = False
        await self.thread.edit(name=f"{self.short_name} with {self.host.name}!")

        random.shuffle(self.players)

        if self.settings.points_to_win == 0:
            rules = (
                "This is a **zero-point** game, so **the first player to get rid of all their cards "
                "wins the entire game**."
            )
        else:
            rules = f"For this UNO game, the first player to reach **{self.settings.points_to_win} points** wins."

        with support.Assets.uno():
            funny = (
                random.choice(open("uno_start_lines.txt").readlines()).strip() + "\n\n"
            )

        with shrine.Torii.uno() as torii:
            template = torii.get_template("game-start.md")
            msg = template.render(funny=funny, rules=rules)

        embed = discord.Embed(
            title="Let's play UNO!", description=msg, color=support.Color.mint()
        )

        with support.Assets.uno():
            uno_logo = discord.File("uno_logo.png", filename="uno_logo.png")
            embed.set_image(url="attachment://uno_logo.png")

            await self.thread.send(content="@everyone", embed=embed, file=uno_logo)

        await asyncio.sleep(3)

        await self.start_round()

    async def add_player(
        self, ctx: discord.ApplicationContext, user: discord.User, *, is_host=False
    ):
        """
        Add a player to the game.

        Parameters
        ----------
        ctx : discord.ApplicationContext
        user : discord.Member
            The user object of the player being added.
        is_host : bool
            Whether the player being added is the Game Host.
        """
        if user not in await self.thread.fetch_members():
            await self.thread.add_user(user)

        player = UnoPlayer(user=user, game=self)
        self.players.append(player)

        join_message_embed = discord.Embed(
            title="A new player has joined the game!",
            description=f"{user.mention} joined the game. Say hello!",
            color=support.Color.mint(),
        )

        await self.thread.send(embed=join_message_embed)

        if self.voice_channel:
            await self.voice_channel.set_permissions(
                target=player.user, overwrite=player.voice_overwrites()
            )

        if not is_host:
            msg = (
                f"If you didn't mean to join, you can leave the game with `/uno ciao > Leave Game`. You can leave "
                f"at any time, but if the game has already started, you won't be able to rejoin.\n"
                f"\n"
                f"Be advised that the Game Host, {self.host.mention}, can kick you at any time, "
                f"and if you go AFK mid-game, I'll have you automatically removed for inactivity. Please remember "
                f"to be courteous to your fellow players.\n"
                f"\n"
                f"Have fun!"
            )

            embed = discord.Embed(
                title=f"Welcome to UNO, {user.name}!",
                description=msg,
                color=support.Color.mint(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

    async def remove_player(self, player_node: dllistnode):
        """
        Remove a player from the game.

        Parameters
        ----------
        player_node : dllistnode
            The node of the player to remove.
        """

        player: UnoPlayer = player_node.value

        embed = discord.Embed(
            title="A player has left the game.",
            description=f"{player.user.mention} has left the game.",
            color=support.Color.error(),
        )

        await self.thread.send(embed=embed)

        # if the host leaves, the game is force closed
        if player.user == self.host:
            await self.force_close(reason="host_left")

        # if there are fewer than two players remaining in the game and the game has started, the game is force closed
        elif len(self.players) - 1 < self.min_players and not self.is_joinable:
            await self.force_close(reason="insufficient_players")

        elif not self.current_player == player_node and not self.is_joinable:
            await player.end_turn()

        self.players.remove(player_node)

        if self.voice_channel and player.user in self.voice_channel.members:
            await player.user.move_to(None)
            await self.voice_channel.set_permissions(target=player.user, overwrite=None)

    async def walk_players(
        self, player_node: dllistnode, steps: int, *, use_value=False
    ) -> dllistnode | UnoPlayer:
        """
        Circularly traverse the list of a game's players.

        Parameters
        ----------
        player_node : dllistnode
            The node of the player to start traversing from.
        steps : int
            The number of steps to traverse.
        use_value : bool
            Whether to return the node or its value.

        Returns
        -------
        dllistnode | UnoPlayer
            The node or value of the player at the end of the traversal.
        """
        for step in range(steps):
            if self.reverse_turn_order:
                # we traverse backwards if a reverse card is in effect
                player_node = player_node.prev or self.players.last
            else:
                player_node = player_node.next or self.players.first

        if use_value:
            return player_node.value
        else:
            return player_node

    async def start_round(self):
        """
        Start a new round of an UNO game.
        """
        self.current_round += 1
        self.reverse_turn_order = False
        self.card_in_play = None
        self.status.previous_turn_record.clear()

        for player in self.players.itervalues():
            player.hand.clear()  # clear that motherfucker out
            await player.add_cards(7)

        msg = f"Round {self.current_round} has begun!"
        if self.current_round == 1:
            msg += " Seven cards have been dealt to each player. Check them out with `/uno play > View Hand`."
        else:
            msg += (
                " Any cards you had at the end of the previous round have been taken, and seven new cards have "
                "been dealt to each player. Check them out with `/uno play > View Hand`."
            )

        embed = discord.Embed(
            title=f"Round {self.current_round}: Start!",
            description=msg,
            color=support.Color.mint(),
        )

        await self.thread.send(embed=embed)
        await self.start_next_turn()

    async def end_round(self, round_winner: UnoPlayer):
        """
        End the current round of an UNO game.

        Parameters
        ----------
        round_winner : UnoPlayer
            The winner of the round.
        """
        self.current_player = None

        # the number of points awarded to a round's winner is based on the point values of all cards held
        # by the other players at the end of the round. the winner of a round will always be awarded at least
        # one point, even if the cumulative value of every other player's hand is zero.
        awarded_points = (
            sum([player.hand_value for player in self.players.itervalues()]) or 1
        )

        round_winner.points += awarded_points

        winner_rank = self.status.get_player_ranking(round_winner)

        msg = (
            f"Congratulations, {round_winner.user.mention}! You won Round {self.current_round}!\n"
            f"\n"
            f"Based on the cards everyone else is holding, {round_winner.user.name} has been awarded "
            f"**{awarded_points} points**.\n"
            f"\n"
            f"{round_winner.user.name} currently has **{round_winner.points} points**, putting them in "
            f"**{winner_rank} place**"
        )

        if (point_gap := self.settings.points_to_win - round_winner.points) > 0:
            msg += f"—{inflect.no('point', point_gap)} away from winning the game"

        msg += ". To view the full leaderboard, use `/uno status`."

        embed = discord.Embed(
            title=f"Round {self.current_round}: Over! {round_winner.user.name} Wins!",
            description=msg,
            color=support.Color.mint(),
        )

        embed.set_thumbnail(url=round_winner.user.display_avatar.url)

        await self.thread.send(content="@everyone", embed=embed)

        if round_winner.points >= self.settings.points_to_win:
            await self.end_game(game_winner=round_winner)
        else:
            await asyncio.sleep(5)
            await self.start_round()

    async def start_next_turn(self):
        """
        Starts the next player's turn.
        """
        self.status.num_turns += 1
        self.turn_uuid = uuid.uuid4()

        if self.current_player is None:
            self.current_player = self.players.first
        elif self.skip_next_player:
            self.current_player = await self.walk_players(self.current_player, 2)
            self.skip_next_player = False
        else:
            self.current_player = await self.walk_players(self.current_player, 1)

        embed = discord.Embed(
            title="New Turn",
            description=f"It's {posessive(self.current_player.value.user.name)} turn. "
            f"Make your move with `/uno play`.",
            color=support.Color.white(),
        )

        embed.set_thumbnail(url=self.current_player.value.user.display_avatar.url)

        await self.thread.send(
            content=f"{self.current_player.value.user.mention}, it's your turn.",
            embed=embed,
        )
        await self.turn_timer()

    async def end_turn(self):
        """
        End the current player's turn.
        """
        if self.turn_record:
            await self.thread.send(embeds=self.turn_record)

        self.status.previous_turn_record = self.turn_record.copy()
        self.turn_record.clear()

        round_winner = discord.utils.find(
            lambda player: len(player.hand) == 0, self.players.itervalues()
        )

        if round_winner:
            await self.end_round(round_winner=round_winner)
        else:
            await self.start_next_turn()

    async def end_game(self, game_winner: UnoPlayer):
        """
        End the game. This is only called when a player meets the win condition, and should not be confused
        with force closing the game.
        """
        self.__all_games__.pop(self.thread.id)

        with shrine.Torii.uno() as torii:
            template = torii.get_template("game-over.md")
            msg = template.render(winner=game_winner)

        embed = discord.Embed(
            title=f"Game Over! {game_winner.name} Wins!",
            description=msg,
            color=support.Color.mint(),
        )
        embed.set_thumbnail(url=game_winner.user.display_avatar.url)
        await self.thread.edit(name=f"UNO with {self.host.name} - Game Over!")
        msg = await self.thread.send(
            content="@everyone", embed=embed, view=uno.UnoGameEndView(game=self)
        )
        await msg.pin()

        await asyncio.sleep(60)
        await self.thread.delete()

    async def turn_timer(self):
        """
        Enforces a time limit on how long players can take to move.
        """
        # before the timer is set, the turn's unique identifier is recorded
        turn_uuid = self.turn_uuid

        await asyncio.sleep(support.fuzz(self.settings.timeout))

        # if, after the timer is up, the uuid of the current turn is still the same as the one recorded
        # by the timer, the player times out
        if (
            self.turn_uuid == turn_uuid
            and self.retrieve_game(self.thread.id)
            and self.current_player
        ):
            player: UnoPlayer = self.current_player.value
            player.timeout_counter += 1

            # if *every* player times out consecutively, the game is force closed for inactivity
            if sum(
                player.timeout_counter for player in self.players.itervalues()
            ) >= len(self.players):
                await self.force_close(reason="inactivity")

            # if the player has timed out for three turns in a row, they are removed from the game for inactivity
            elif player.timeout_counter == 3:
                embed = discord.Embed(
                    title=f"{player.user.name} timed out.",
                    description=f"{player.user.name} was removed from the game for inactivity.",
                    color=support.Color.error(),
                )
                await self.thread.send(embed=embed)

                embed = discord.Embed(
                    title=f"You timed out of {posessive(self.host.name)} UNO game.",
                    description=f"You were removed from {self.host.name}'s UNO game in "
                    f"{self.guild.name} for inactivity.",
                    color=support.Color.error(),
                )
                await player.user.send(embed=embed)

                await self.remove_player(self.current_player)

            # if neither of the above conditions are met, the player is forced to draw a card and forfeit their turn
            else:
                await self.processor.turn_timeout_event(player=player)
                await player.end_turn()

    def is_card_playable(self, card: UnoCard):
        """
        Determine whether an :class:`UnoCard` can be played on the current turn.
        """
        return (
            self.card_in_play is None
            or card.versus_color is self.card_in_play.versus_color
            or card.versus_suit is self.card_in_play.versus_suit
            or card.color is UnoCardColor.WILD
        )

    async def transfer_host(self, new_host: discord.User):
        old_host = self.host
        await super().transfer_host(new_host)

        if self.voice_channel:
            await self.voice_channel.set_permissions(
                target=old_host,
                overwrite=self.retrieve_player(old_host).voice_overwrites(),
            )

            await self.voice_channel.set_permissions(
                target=new_host,
                overwrite=self.retrieve_player(new_host).voice_overwrites(),
            )

    async def kick_player(self, player_node: dllistnode):
        """
        Kicks a player from the game.

        Parameters
        ----------
        player_node: dllistnode
            The node of the player to kick.
        """
        embed = discord.Embed(
            title="Player Kicked",
            description=f"{player_node.value.user.mention} has been kicked from the game.",
            color=support.Color.error(),
        )

        await self.thread.send(embed=embed)
        await self.remove_player(player_node)

        embed = discord.Embed(
            title=f"You were kicked from {posessive(self.host.name)} UNO game.",
            description=f"You were kicked from {self.host.name}'s UNO game in {self.guild.name}.",
            color=support.Color.error(),
        )

        embed.timestamp = discord.utils.utcnow()

        await player_node.value.user.send(embed=embed)


class UnoGameSettings(BaseSettings):
    """
    The settings for an :class:`UnoGame`.

    Parameters
    ----------
    max_players: int
        The maximum number of players allowed to join the game.
    points_to_win: int
        The number of points required to win the game.
    timeout: int
        The number of seconds players must finish their turns in before being penalized.
    """

    max_players: int
    points_to_win: int
    timeout: int

    def __str__(self):
        players_str = (
            f"__**Maximum Players**: {self.max_players}__\n"
            f"Up to {self.max_players} players can join this UNO game. Once that quota is filled, "
            f"no one else will be able to join unless a player leaves or is removed by the Game Host."
        )

        points_str = f"__**Points to Win**: {self.points_to_win}__\n"
        if self.points_to_win == 0:
            points_str += (
                "The first player to get rid of all their cards will win the game."
            )
        else:
            points_str += f"The first player to reach {self.points_to_win} points will win the game."

        timeout_str = (
            f"__**Timeout**: {self.timeout} seconds__\n"
            f"Each player will have {self.timeout} seconds to move during their turn. If a player exceeds "
            f"this time limit, they will be forced to draw a card and forfeit their turn."
        )

        return "\n\n".join([players_str, points_str, timeout_str])


class UnoPlayer(BasePlayer):
    """
    A player in an UNO game.

    Parameters
    ----------
    user: :class:`discord.Member`
        The associated Discord user.
    game: :class:`UnoGame`
        The associated game.

    Attributes
    ----------
    points: :class:`int`
        The number of points the player has.
    hand : :class:`SortedKeyList[UnoCard]`
        The cards in the player's posession.
    can_say_uno: :class:`bool`
        Whether the player can say "UNO!".
    has_said_uno: :class:`bool`
        Whether the player has said "UNO!" in the time since their hand was most recently reduced to one card.
    terminable_views : :class:`list[support.View]`
        A list of :class:`uno.views.UnoTerminableView` instances that the player has created.
    timeout_counter: :class:`int`
        The number of consecutive turns on which the player has timed out.
    """

    def __init__(self, user: discord.Member, game: UnoGame):
        super().__init__(user)
        self.game = game

        self.points: int = 0
        self.hand: SortedKeyList[UnoCard] = SortedKeyList(
            key=lambda card: card.sortcode
        )
        self.can_say_uno = False
        self.has_said_uno = False
        self.terminable_views: list[support.View] = []
        self.timeout_counter: int = 0

        # for uno status center
        self.num_cards_played = 0
        self._num_cards_drawn = 0

    async def show_hand(self, ctx: discord.ApplicationContext):
        """
        Shows the player the cards they're currently holding.

        :param ctx: A discord.ApplicationContext object.
        """
        split_cards = support.split_list(self.hand, 23)
        pages = [
            discord.Embed(
                title="Your Hand",
                description=f"Here are all the cards you're currently holding:\n\n"
                f"{chr(10).join([f'- {str(card)} {card.emoji}' for card in page])}",
                color=support.Color.mint(),
            )
            for page in split_cards
        ]

        for embed in pages:
            embed.set_footer(
                text=discord.utils.remove_markdown(self.game.last_move_str)
            )

        paginator = discord_pages.Paginator(
            pages=pages,
            use_default_buttons=False,
            custom_buttons=support.pagimoji(),
        )

        await paginator.respond(ctx.interaction, ephemeral=True)

    async def select_card(self, ctx: discord.ApplicationContext):
        """
        Allows players to select a card to play.

        :param ctx: A discord.ApplicationContext object.
        turn.
        """

        view = uno.UnoCardSelectView(ctx=ctx, player=self, cards=self.hand)
        selected_card: UnoCard = await view.select_card()

        if selected_card:
            # inform the player about saying 'UNO!' if playing the card will leave them with only one card in their hand
            if len(self.hand) == 2:
                msg = (
                    'After playing this card, you"re required to say "UNO!" `(/uno play > "Say UNO!")` or risk '
                    "being called out by other players.\n"
                    "\n"
                    "Play this card?"
                )
                embed = discord.Embed(
                    title="One Card Remaining",
                    description=msg,
                    color=support.Color.caution(),
                )

                view = uno.UnoTerminableConfView(ctx=ctx)
                confirmation = await view.request_confirmation(
                    prompt_embeds=[embed], ephemeral=True, edit=True
                )

                if confirmation:
                    if selected_card.color is not UnoCardColor.WILD:
                        await ctx.interaction.edit_original_response(
                            content="Good luck! 🤞🏾", embeds=[], view=None
                        )
                else:
                    await ctx.interaction.edit_original_response(
                        content="Okay! Make your move whenever you're ready.",
                        embeds=[],
                        view=None,
                    )

                    return

            # present color selection view if the player selects a wild card, provided it isn't the last card in
            # their hand
            if selected_card.color is UnoCardColor.WILD and len(self.hand) > 1:
                view = uno.WildColorSelectView(ctx=ctx, player=self, card=selected_card)
                selected_card = await view.choose_color()

                if selected_card.transformation:
                    # only play the card if the player selected a color
                    await self.play_card(selected_card)
            else:
                await self.play_card(selected_card)

    async def play_card(self, card: UnoCard, with_draw: bool = False):
        """
        Play an UNO card.

        Parameters
        ----------
        card: :class:`UnoCard`
            The card to play.
        with_draw: :class:`bool`
            Whether the card is being played automatically after being drawn.
        """
        await self.reset_timeouts()

        # remove the card from the player's hand
        self.hand.remove(card)
        self.num_cards_played += 1

        await self.game.processor.card_played_event(
            player=self, card=card, with_draw=with_draw
        )

        await self.end_turn()

    async def draw_card(self, ctx: discord.ApplicationContext):
        """
        Draws an UNO card.

        Parameters
        ----------
        ctx: :class:`discord.ApplicationContext`
        """

        view = uno.UnoDrawCardView(ctx=ctx)
        await view.draw_card()

        if view.success:
            await self.reset_timeouts()

            drawn_card = await self.add_cards(1)

            card = drawn_card[0]

            if (
                view.autoplay
                and self.game.is_card_playable(card)
                and card.color is not UnoCardColor.WILD
            ):
                # play the card if it can be played on the current turn and isn't a wild or wild draw four
                embed = discord.Embed(
                    title="Card Drawn and Played",
                    description=f"You drew and played a **{str(card)}**.",
                    color=card.embed_color,
                )
                embed.set_thumbnail(url=card.emoji.url)

                await ctx.interaction.edit_original_response(embeds=[embed], view=None)

                if len(self.hand) - 1 == 1:
                    embed = discord.Embed(
                        title="One Card Remaining",
                        description="You'll need to say 'UNO!' or risk being called out by "
                        "other players.",
                        color=support.Color.caution(),
                    )

                    await ctx.interaction.followup.send(embed=embed, ephemeral=True)

                await self.play_card(card, with_draw=True)
            else:
                embed = discord.Embed(
                    title="Card Drawn",
                    description=f"You drew a **{str(card)}**.",
                    color=card.embed_color,
                )
                embed.set_thumbnail(url=card.emoji.url)

                await ctx.interaction.edit_original_response(embeds=[embed], view=None)

                await self.game.processor.card_drawn_event(player=self)

                await self.end_turn()
        elif view.success is False:
            msg = "Okay! Make your move whenever you're ready."
            await ctx.interaction.edit_original_response(
                content=msg, embeds=[], view=None
            )

    async def say_uno(self):
        """
        Say 'UNO!'.
        """
        await self.game.processor.say_uno_event(player=self)

    async def callout(self, ctx: discord.ApplicationContext):
        """
        Call out a player for having one remaining card and failing to say 'UNO!'.

        Parameters
        ----------
        ctx: :class:`discord.ApplicationContext`
        """
        target = await uno.UnoCalloutView(ctx=ctx).present()

        if target.can_say_uno and not target.has_said_uno:
            embed = discord.Embed(
                title="The callout succeeds!",
                description=f"{target.user.name} draws two cards.",
                color=support.Color.green(),
            )

            await ctx.interaction.edit_original_response(embeds=[embed], view=None)
            await self.game.processor.callout_event(
                challenger=self, target=target, callout_success=True
            )
        else:
            embed = discord.Embed(
                title="The callout fails.",
                description="You draw a card and forfeit your turn.",
                color=support.Color.brand_red(),
            )

            await ctx.interaction.edit_original_response(embeds=[embed], view=None)
            await self.game.processor.callout_event(
                challenger=self, target=target, callout_success=False
            )
            await self.end_turn()

    async def add_cards(self, num_cards):
        """
        Add cards to the player's hand.

        Parameters
        ----------
        num_cards: :class:`int`
            The number of cards to add.
        """
        new_cards = UnoCard.generate_cards(num_cards)

        self.num_cards_drawn += num_cards

        self.hand.update(new_cards)

        self.can_say_uno = False
        self.has_said_uno = False

        return new_cards

    def voice_overwrites(self) -> discord.Permissions:
        """
        Returns the voice channel permission overwrites for the player.
        """
        if self.game.host == self.user:
            overwrites = {
                "allow": support.GamePermissions.vc(),
                "deny": discord.Permissions.none(),
            }
        else:
            overwrites = {
                "allow": discord.Permissions(
                    connect=True, speak=True, use_voice_activation=True
                ),
                "deny": discord.Permissions.none(),
            }

        overwrites["allow"] += discord.Permissions(
            view_channel=True, read_message_history=True
        )

        return discord.PermissionOverwrite.from_pair(**overwrites)

    async def reset_timeouts(self):
        """
        Resets the player's timeout counter to 0.
        """
        self.timeout_counter = 0

    async def end_turn(self):
        """
        Ends the player's turn.
        """
        for view in self.terminable_views:
            if not view.is_finished():
                await view.full_stop()

        if len(self.hand) == 1 and not self.has_said_uno:
            self.can_say_uno = True

        await self.game.end_turn()

        self.terminable_views.clear()

    @property
    def hand_value(self):
        """
        The collective value of all cards in the player's hand.

        See Also
        --------
        :attr:`UnoCard.point_value`
        """
        return sum(card.point_value for card in self.hand)

    @property
    def num_cards_drawn(self):
        """
        The total number of cards the player has drawn.

        Notes
        -----
        This is defined as a property rather than a normal instance attribute so that its value can be
        dynamically altered to exclude the seven cards dealt to each player at the start of a round.
        """
        # where d1 includes dealt cards and d2 does not:
        # d2 = d1 - (7 * round_number) OR d2 = 0, whichever is higher
        return max(self._num_cards_drawn - (7 * self.game.current_round), 0)

    @num_cards_drawn.setter
    def num_cards_drawn(self, value):
        self._num_cards_drawn += value

    def __str__(self):
        return self.user.name


# apparently, you're not supposed to try this at home
class _UnoCardAttrMeta(EnumMeta):
    """
    Metaclass for :class:`_UnoCardAttr`.
    """

    def iterd(cls):
        """
        Iterate over all non-special attributes.

        Notes
        -----
        Equivalent to :meth:`__iter__`, which simply returns this method's result.
        """
        for attr in super().__iter__():
            if attr not in cls._special:
                yield attr

    def iters(cls):
        """
        Iterate over all special attributes.
        """
        for attr in super().__iter__():
            if attr in cls._special:
                yield attr

    def itera(cls):
        """
        Iterate over all attributes.
        """
        return super().__iter__()

    def index(cls, value):
        """
        Get the index of the given attribute within its enumeration.

        Parameters
        ----------
        value : _UnoCardAttr
            The attribute to get the index of.

        Returns
        -------
        int
            The index of the attribute.
        """
        return list(cls.itera()).index(value)

    @property
    def _special(cls):
        return UnoCardColor.WILD, UnoCardSuit.DRAW_FOUR, UnoCardSuit.NONE

    def __iter__(self):
        return self.iterd()


class _UnoCardAttr(Enum, metaclass=_UnoCardAttrMeta):
    """
    Base enumeration for :class:`UnoCardColor` and :class:`UnoCardSuit`.
    """

    def casefold(self):  # temporary backwards-compatibility patch; remove eventually
        return str(self).casefold()

    @property
    def emoji_key(self):
        return self.name.lower()

    @property
    def sortcode(self):
        return self.__class__.index(self)

    def __str__(self):
        return str(self.value).title()


class UnoCardColor(_UnoCardAttr):
    """
    Enumerates UNO card colors.
    """

    # Default
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"

    # Special
    WILD = "wild"


class UnoCardSuit(_UnoCardAttr):
    """
    Enumerates UNO card suits.
    """

    # Default
    ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE = string.digits
    REVERSE = "reverse"
    SKIP = "skip"
    DRAW_TWO = "+2"

    # Special
    NONE = None
    DRAW_FOUR = "+4"

    def __bool__(self):
        return self is not self.NONE


class UnoCard:
    """
    An UNO card.

    Parameters
    ----------
    color: :class:`UnoCardColor`
        The color of the card.
    suit: :class:`UnoCardSuit`
        The suit of the card.
    """

    def __init__(self, color: UnoCardColor, suit: UnoCardSuit = UnoCardSuit.NONE):
        self._color = color
        self._suit = suit

        self._transformation = None
        self._uuid = uuid.uuid4().hex

    @classmethod
    def generate_cards(cls, num_cards) -> list[UnoCard]:
        """
        Generate UNO cards of random canonical color-suit combinations.

        Parameters
        ----------
        num_cards
            The number of cards to generate.

        Returns
        -------
        :class:`list` of :class:`UnoCard`
            The generated cards.

        Notes
        -----
        This algorithm has an equal chance of generating any one of the 54 distinct UNO cards in a standard deck.
        This does not emulate the probability of drawing cards in the canonical implementation of UNO, in which
        cards appear with varying frequencies.
        """
        cards = [
            *[(color, suit) for color in UnoCardColor for suit in UnoCardSuit],
            *[
                (color, suit)
                for color in UnoCardColor.iters()
                for suit in UnoCardSuit.iters()
            ],
        ]

        return [cls(*card) for card in random.choices(cards, k=num_cards)]

    @property
    def color(self) -> UnoCardColor:
        """
        The color of the card.
        """
        return self._color

    @property
    def suit(self) -> UnoCardSuit:
        """
        The suit of the card.
        """
        return self._suit

    @property
    def versus_color(self) -> UnoCardColor:
        """
        The color to be used when checking if this card is playable against another.
        """
        return self.transformation or self.color

    @property
    def versus_suit(self) -> UnoCardSuit:
        """
        The suit to be used when checking if this card is playable against another.

        Notes
        -----
        This property is equivalent to :attr:`UnoCard.suit` and exists only for consistency with
        :attr:`UnoCard.versus_color`.
        """
        return self.suit

    @property
    def transformation(self) -> UnoCardColor | None:
        """
        The color the card was changed to. Only applicable to Wild cards.

        Returns
        -------
        :class:`UnoCardColor` | None
            If this is a Wild card, returns the card's new color if it has been set. Otherwise, returns None.
        """
        return self._transformation

    @transformation.setter
    def transformation(self, value: UnoCardColor):
        if self.color is not UnoCardColor.WILD:
            raise ValueError("transformation can only be set on Wild cards")

        self._transformation = value

    @property
    def emoji(self) -> discord.PartialEmoji:
        """
        The card's corresponding Discord emoji.
        """
        with support.Assets.uno():
            card_emoji = toml.load(open("uno_card_emotes.toml"))
            return discord.PartialEmoji.from_str(
                card_emoji[self.color.emoji_key][self.suit.emoji_key]
            )

    @property
    def point_value(self) -> int:
        """
        The card's point value.
        """

        # wild and wild draw four cards are worth 50 points
        if self.color is UnoCardColor.WILD:
            return 50

        # reverse, skip, and draw two cards are worth 20 points
        elif self.suit in [UnoCardSuit.REVERSE, UnoCardSuit.SKIP, UnoCardSuit.DRAW_TWO]:
            return 20

        # otherwise, it's a numbered card and worth its face value
        else:
            return int(self.suit.value)

    @property
    def embed_color(self) -> support.Color:
        """
        The card's corresponding embed color.
        """

        embed_colors = {
            UnoCardColor.RED: support.Color.brand_red(),
            UnoCardColor.BLUE: support.Color.blue(),
            UnoCardColor.GREEN: support.Color.green(),
            UnoCardColor.YELLOW: support.Color.yellow(),
            UnoCardColor.WILD: support.Color.black(),
        }

        return embed_colors[self.color]

    @property
    def transformation_embed_color(self) -> support.Color:
        """
        The embed color corresponding to the card's transformation. Only applicable to Wild cards.
        """
        if self.color is not UnoCardColor.WILD:
            raise ValueError(
                "transformation_embed_color may only be accessed on Wild cards"
            )

        if not self.transformation:
            raise ValueError(
                "transformation must be set before transformation_embed_color can be accessed"
            )

        embed_colors = {
            UnoCardColor.RED: support.Color.brand_red(),
            UnoCardColor.BLUE: support.Color.blue(),
            UnoCardColor.GREEN: support.Color.green(),
            UnoCardColor.YELLOW: support.Color.yellow(),
        }

        return embed_colors[self.transformation]

    @property
    def sortcode(self) -> int:
        """
        An integer to be used as a key when sorting this card among others.

        Extended Summary
        ----------------
        An integer to be used as a key to enforce the sorting of :class:`UnoCard` objects by color in order of:
            RED, BLUE, GREEN, YELLOW, WILD
        and then by suit in order of:
            ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE, REVERSE, SKIP, DRAW_TWO, NONE, DRAW_FOUR
        where each color and suit corresponds to a member of :class:`UnoCardColor` and :class:`UnoCardSuit`,
        respectively.

        Notes
        -----
        - This sorting mechanism divides cards of each color into 100-point intervals, with each suit occupying one
          point within its color space.

        - Using this property as a sort key is preferred over implementing comparison operators on :class:`UnoCard`
          to avoid ambiguity over what "less than", "greater than", and "equal to" mean with respect to objects
          of the class.

        Returns
        -------
        :class:`int`
            The card's sort code.
        """
        return self.color.sortcode * 100 + self.suit.sortcode

    @property
    def uuid(self) -> str:
        """
        The card's hexademical UUID.
        """
        return self._uuid

    def __str__(self):
        return f"{self.color} {self.suit}" if self.suit else str(self.color)


class UnoEventProcessor:
    """
    Processes game events.

    Parameters
    ----------
    game: :class:`UnoGame`
    """

    def __init__(self, game: UnoGame):
        self.game = game

    async def card_played_event(
        self, player: UnoPlayer, card: UnoCard, with_draw: bool = False
    ):
        """
        The handler for the event of playing a card.

        Parameters
        ----------
        player: :class:`UnoPlayer`
            The player who played the card.
        card: :class:`UnoCard`
            The card that was played.
        with_draw: :class:`bool`
            Whether the card was played in conjunction with a draw.
        """
        self.game.card_in_play = card

        embed = discord.Embed(
            title=f"Card {'Drawn and ' if with_draw else ''}Played",
            description=f"**{player.user.name}** {'draws and' if with_draw else ''} "
            f"plays a **{str(card)}**.",
            color=card.embed_color,
        )

        embed.set_thumbnail(url=card.emoji.url)
        embed.set_footer(
            icon_url=player.user.display_avatar.url,
            text=f"{player.user} • UNO with {self.game.host.name}! • Round {self.game.current_round}",
        )

        self.game.turn_record.append(embed)

        if card.color is UnoCardColor.WILD:
            await self.wild_event(player=player)

        match card.suit:
            case UnoCardSuit.DRAW_TWO:
                await self.draw_two_event()
            case UnoCardSuit.DRAW_FOUR:
                await self.draw_four_event()
            case UnoCardSuit.SKIP:
                await self.skip_event()
            case UnoCardSuit.REVERSE:
                await self.reverse_event()

    async def card_drawn_event(self, player: UnoPlayer):
        """
        The handler for the event of drawing a card.

        Parameters
        ----------
        player: :class:`UnoPlayer`
            The player who drew the card.
        """
        embed = discord.Embed(
            title="Card Drawn",
            description=f"**{player.user.name}** draws a card.",
            color=support.Color.greyple(),
        )

        embed.set_thumbnail(url=player.user.display_avatar.url)
        embed.set_footer(
            icon_url=player.user.display_avatar.url,
            text=f"{player.user} • UNO with {self.game.host.name}! • Round {self.game.current_round}",
        )

        self.game.turn_record.append(embed)

    async def draw_two_event(self):
        """
        The handler for the event of a +2 card being played.
        """
        self.game.skip_next_player = True

        next_player: UnoPlayer = await self.game.walk_players(
            self.game.current_player, 1, use_value=True
        )
        await next_player.add_cards(2)

        self.game.turn_record[-1].add_field(
            name="🎬 Take Two!",
            value=f"**{next_player.user.name}** draws two cards and "
            f"forfeits their turn.",
            inline=False,
        )

    async def draw_four_event(self):
        """
        The handler for the event of a +4 card being played.
        """
        self.game.skip_next_player = True

        next_player: UnoPlayer = await self.game.walk_players(
            self.game.current_player, 1, use_value=True
        )
        await next_player.add_cards(4)

        self.game.turn_record[-1].add_field(
            name="🍀 Four Score!",
            value=f"**{next_player.user.name}** draws four cards and "
            f"forfeits their turn.",
            inline=False,
        )

    async def skip_event(self):
        """
        The handler for the event of a Skip card being played.
        """
        self.game.skip_next_player = True

        skipped_player = await self.game.walk_players(
            self.game.current_player, 1, use_value=True
        )

        self.game.turn_record[-1].add_field(
            name="⏩ Fast Forward!",
            value=f"**{posessive(skipped_player.user.name)}** turn is skipped.",
            inline=False,
        )

    async def reverse_event(self):
        """
        The handler for the event of a Reverse card being played.
        """
        self.game.reverse_turn_order = not self.game.reverse_turn_order

        if len(self.game.players) == 2:
            self.game.skip_next_player = True

        self.game.turn_record[-1].add_field(
            name="🔄 Reverse, Reverse!",
            value="The turn order is reversed.",
            inline=False,
        )

    async def wild_event(self, player: UnoPlayer):
        """
        The handler for the event of a Wild card being played.

        Parameters
        ----------
        player: :class:`UnoPlayer`
            The player who played the Wild card.
        """

        card = self.game.card_in_play

        color_emoji = {
            UnoCardColor.RED: "🔴",
            UnoCardColor.BLUE: "🔵",
            UnoCardColor.GREEN: "🟢",
            UnoCardColor.YELLOW: "🟡",
        }
        self.game.turn_record[-1].add_field(
            name="🎲 A Wild card appears!",
            value=f"**{player.user.name}** changes the color in play to "
            f"**{color_emoji[card.transformation]} {card.transformation}**.",
            inline=False,
        )

    async def say_uno_event(self, player: UnoPlayer):
        """
        The handler for the event of a a player saying 'UNO!'.

        Parameters
        ----------
        player: :class:`UnoPlayer`
            The player who said 'UNO!'.
        """
        player.can_say_uno = False
        player.has_said_uno = True

        embed = discord.Embed(
            title=f"{player.user.name} says UNO!",
            description=f"**{player.user.mention}** has one card left.",
            color=support.Color.caution(),
        )

        await self.game.thread.send(content="@everyone", embed=embed)

    async def turn_timeout_event(self, player: UnoPlayer):
        """
        The handler for the event of a player's turn timing out.

        :param player: The player whose turn timed out.
        """
        await player.add_cards(1)

        embed = discord.Embed(
            title=f"{player.user.name} timed out.",
            description=f"{player.user.mention} took too long to move and was forced to draw a card.",
            color=support.Color.error(),
        )

        self.game.turn_record.append(embed)

    async def callout_event(
        self, challenger: UnoPlayer, target: UnoPlayer, callout_success: bool
    ):
        """
        The handler for the event of a player calling out another player.

        Parameters
        ----------
        challenger: :class:`UnoPlayer`
            The player making the callout.
        target: :class:`UnoPlayer`
            The player being called out.
        callout_success: :class:`bool`
            Whether or not the callout was successful.
        """

        msg = (
            f"{challenger} calls out {target} for having one card left and failing to say "
            f"'UNO!'."
        )

        embed = discord.Embed(
            title=f"📢 {challenger.user.name} calls out {target}!",
            description=msg,
            color=support.Color.nitro_pink(),
        )

        if callout_success:
            await target.add_cards(2)

            field = (
                f"\n\n**The callout succeeds!** {target} draws two cards.\n"
                f"\n"
                f"It's still {challenger.mention}'s turn."
            )

            embed.add_field(name="The callout succeeds!", value=field)

            await self.game.thread.send(embed=embed)
        else:
            await challenger.add_cards(1)

            field = f"\n\n**The callout fails!** {challenger} draws a card and forfeits their turn."

            embed.add_field(name="The callout fails!", value=field)

            self.game.turn_record.append(embed)


class UnoStatusTracker:
    """
    Tracks game statistics.
    """

    def __init__(self, game: UnoGame):
        self.game = game

        self.num_turns = 0
        self.total_cards_played = 0
        self.total_cards_drawn = 0
        self.previous_turn_record = []

    def get_game_settings(self) -> str:
        """
        Returns a string representation of the game settings.
        """
        return str(self.game.settings)

    def get_player_list(self) -> t.Iterator[UnoPlayer]:
        """
        Returns an iterator over of all players in the game.
        """
        return self.game.players.itervalues()

    async def get_turn_order(self) -> list[UnoPlayer]:
        """
        Return an iterator players in the game in turn order.

        Notes
        -----
        This method's output is affected by whether the turn order is currently reversed.
        """
        turn_order = [self.game.current_player]

        for _ in range(len(self.game.players) - 1):
            turn_order.append(await self.game.walk_players(turn_order[-1], 1))

        return [player.value for player in turn_order]

    def get_last_turn(self) -> list[discord.Embed]:
        """
        Returns a list of :class:`discord.Embed` objects representing the events of the previous turn.
        """
        return self.previous_turn_record

    def get_leaderboard(self) -> list[list[UnoPlayer]]:
        """
        Returns a list of all players in the game, sorted in descending order by score.

        Notes
        -----
        To be more precise,
        this method returns a list of lists of :class:`UnoPlayer` objects - players who have the same score
        are grouped together in the same sub-list.
        """
        point_order = reversed(
            SortedKeyList(self.game.players.itervalues(), key=lambda p: p.points)
        )

        leaderboard = []
        determinant = 0
        for player in point_order:
            if not leaderboard or player.points < determinant:
                determinant = player.points
                leaderboard.append([player])
            else:
                leaderboard[-1].append(player)

        return leaderboard

    def get_player_ranking(self, player, *, with_desc=False) -> str:
        """
        Returns a string representation of the player's ranking in the game.

        Parameters
        ----------
        player: :class:`UnoPlayer`
            The player whose ranking is to be returned.
        with_desc: :class:`bool`
            If True, this function returns an extended description of the player's ranking.
        """
        leaderboard_group = discord.utils.find(
            lambda group: player in group, self.get_leaderboard()
        )
        ranking = inflect.ordinal(self.get_leaderboard().index(leaderboard_group) + 1)

        if with_desc:
            ranking += f" of {len(self.game.players)}"
            ties = len(leaderboard_group) - 1

            if ties:
                ranking += f" (tied with {inflect.no('other', ties)})"

        return ranking

    def get_player_stats(self, player: UnoPlayer) -> dict:
        """
        Returns a dictionary of statistics for the given player.
        """
        return {
            "Rank": self.get_player_ranking(player, with_desc=True),
            "Points": player.points,
            "Cards Held": len(player.hand),
            "Hand Value": player.hand_value,
            "Cards Played": player.num_cards_played,
            "Cards Drawn": player.num_cards_drawn,
        }
