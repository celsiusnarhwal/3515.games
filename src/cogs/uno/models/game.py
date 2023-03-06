########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import asyncio
import random
import uuid

import discord
import inflect as ifl
from attr import define
from elysia import Fields
from llist import dllist, dllistnode

import shrine
import support
from cogs import uno
from keyboard import *
from shrine.kami import posessive
from support import HostedGame

inflect = ifl.engine()


@define(slots=False)
class UnoGame(HostedGame):
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

    __games__: ClassVar = {}

    name: ClassVar = "UNO"
    min_players: ClassVar = 2

    settings: UnoGameSettings

    players: dllist = Fields.attr(factory=dllist)
    current_round: int = Fields.attr(default=0)
    current_player: dllistnode = Fields.attr(default=None)
    skip_next_player: bool = Fields.attr(default=False)
    reverse_turn_order: bool = Fields.attr(default=False)
    turn_uuid: uuid.UUID = Fields.attr(default=None)
    card_in_play: uno.UnoCard = Fields.attr(default=None)
    turn_record: list[discord.Embed] = Fields.attr(factory=list)

    def __attrs_post_init__(self):
        self.status = uno.UnoStatusTracker(self)
        self.processor = uno.UnoEventProcessor(self)

    @property
    def last_move_str(self):
        """
        A string describing the last card played. In the case of a Wild card, this also describes the color in play.
        """
        if self.card_in_play:
            last_move = f"The last card played was a **{self.card_in_play}**."

            if self.card_in_play.color is uno.UnoCardColor.WILD:
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
    ) -> uno.UnoPlayer | dllistnode:
        """
        Retrieve a player from the game given their corresponding :class:`discord.Member` object.

        Parameters
        ----------
        user : discord.Member

        return_node : bool
            Whether to return the player's :class:`llist.dllistnode` object rather than their
            :class:`uno.UnoPlayer` object.

        Returns
        -------
        uno.UnoPlayer | llist.dllistnode
            The player's :class:`uno.UnoPlayer` object, or their :class:`llist.dllistnode`
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
            funny = random.choice(open("comedy.txt").readlines()).strip() + "\n\n"

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

        player = uno.UnoPlayer(user=user, game=self)
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

        player: uno.UnoPlayer = player_node.value

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
    ) -> dllistnode | uno.UnoPlayer:
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
        dllistnode | uno.UnoPlayer
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

    async def end_round(self, round_winner: uno.UnoPlayer):
        """
        End the current round of an UNO game.

        Parameters
        ----------
        round_winner : uno.UnoPlayer
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

    async def end_game(self, game_winner: uno.UnoPlayer):
        """
        End the game. This is only called when a player meets the win condition, and should not be confused
        with force closing the game.
        """
        self.kill()

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
            player: uno.UnoPlayer = self.current_player.value
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

    def is_card_playable(self, card: uno.UnoCard):
        """
        Determine whether an :class:`uno.UnoCard` can be played on the current turn.
        """
        return (
            self.card_in_play is None
            or card.versus_color is self.card_in_play.versus_color
            or card.versus_suit is self.card_in_play.versus_suit
            or card.color is uno.UnoCardColor.WILD
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


@define(frozen=True)
class UnoGameSettings:
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


@define
class UnoEventProcessor:
    """
    Processes game events.

    Parameters
    ----------
    game: :class:`UnoGame`
    """

    game: uno.UnoGame

    async def card_played_event(
        self, player: uno.UnoPlayer, card: uno.UnoCard, with_draw: bool = False
    ):
        """
        The handler for the event of playing a card.

        Parameters
        ----------
        player: :class:`uno.UnoPlayer`
            The player who played the card.
        card: :class:`uno.UnoCard`
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

        if card.color is uno.UnoCardColor.WILD:
            await self.wild_event(player=player)

        match card.suit:
            case uno.UnoCardSuit.DRAW_TWO:
                await self.draw_two_event()
            case uno.UnoCardSuit.DRAW_FOUR:
                await self.draw_four_event()
            case uno.UnoCardSuit.SKIP:
                await self.skip_event()
            case uno.UnoCardSuit.REVERSE:
                await self.reverse_event()

    async def card_drawn_event(self, player: uno.UnoPlayer):
        """
        The handler for the event of drawing a card.

        Parameters
        ----------
        player: :class:`uno.UnoPlayer`
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

        next_player: uno.UnoPlayer = await self.game.walk_players(
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

        next_player: uno.UnoPlayer = await self.game.walk_players(
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

    async def wild_event(self, player: uno.UnoPlayer):
        """
        The handler for the event of a Wild card being played.

        Parameters
        ----------
        player: :class:`uno.UnoPlayer`
            The player who played the Wild card.
        """

        card = self.game.card_in_play

        color_emoji = {
            uno.UnoCardColor.RED: "🔴",
            uno.UnoCardColor.BLUE: "🔵",
            uno.UnoCardColor.GREEN: "🟢",
            uno.UnoCardColor.YELLOW: "🟡",
        }
        self.game.turn_record[-1].add_field(
            name="🎲 A Wild card appears!",
            value=f"**{player.user.name}** changes the color in play to "
            f"**{color_emoji[card.transformation]} {card.transformation}**.",
            inline=False,
        )

    async def say_uno_event(self, player: uno.UnoPlayer):
        """
        The handler for the event of a a player saying 'UNO!'.

        Parameters
        ----------
        player: :class:`uno.UnoPlayer`
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

    async def turn_timeout_event(self, player: uno.UnoPlayer):
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
        self,
        challenger: uno.UnoPlayer,
        target: uno.UnoPlayer,
        callout_success: bool,
    ):
        """
        The handler for the event of a player calling out another player.

        Parameters
        ----------
        challenger: :class:`uno.UnoPlayer`
            The player making the callout.
        target: :class:`uno.UnoPlayer`
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
