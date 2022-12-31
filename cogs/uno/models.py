########################################################################################################################
#                         Copyright (C) 2022-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import asyncio
import copy
import random
import string
import uuid
from enum import Enum, EnumMeta
from typing import Union

import discord
import inflect as ifl
import tomlkit as toml
from discord.ext import pages as discord_pages
from llist import dllistnode, dllist as DoublyLinkedList
from sortedcontainers import SortedKeyList

import support
from cogs import uno
from support import HostedMultiplayerGame, posessive

inflect = ifl.engine()


class UnoGame(HostedMultiplayerGame):
    """
    Represents an UNO game.
    """
    name = "UNO"

    def __init__(self, settings: UnoGameSettings, *args, **kwargs):
        """
        The constructor for ``UnoGame``.

        :param guild: The server (a.k.a. "guild") in which the game is taking place.
        :param thread: The game's associated thread.
        :param host: The user who is the Game Host.
        :param settings: The UnoGameSettings object representing the game's settings.
        """

        super().__init__(*args, **kwargs)

        self.settings: UnoGameSettings = settings

        self.players = DoublyLinkedList()
        self.is_joinable: bool = True
        self.current_round: int = 0
        self.current_player = dllistnode()
        self.skip_next_player = False
        self.reverse_turn_order = False
        self.turn_uuid = None
        self.last_move = None
        self.card_in_play: UnoCard = None
        self.color_in_play: str = ""
        self.suit_in_play: str = ""
        self.lobby_intro_msg: discord.Message = None
        self.turn_record = []
        self.status = UnoStatusCenter(game=self)

        self.__all_games__[self.thread.id] = self

    async def game_timer(self):
        """
        Imposes a 12-hour time limit within which an UNO game must be completed.
        """
        await asyncio.sleep(43200)

        if self.retrieve_game(self.thread.id):
            await self.force_close(reason="time_limit")

    def retrieve_player(self, user, return_node=False) -> Union[UnoPlayer, dllistnode]:
        """
        Retrieves a player from ``UnoGame().players`` given that player's user object.

        :param user: The object corresponding to the player. This can be a discord.User, discord.Member, or
        discord.ThreadMember object.
        :param return_node: If True, the player's dllistnode will be returned instead of their UnoPlayer object.
        :return: An UnoPlayer object.
        """

        if return_node:
            return discord.utils.find(lambda node: node.value.user.id == user.id, self.players.iternodes())
        else:
            return discord.utils.find(lambda player: player.user.id == user.id, self.players.itervalues())

    async def open_lobby(self):
        """
        Sends an introductory message at the creation of an UNO game thread and pins said message to that thread.
        """
        intro_message = f"{self.host.mention} is the Game Host.\n" \
                        f"\n" \
                        f"To **join**, type `/uno join`. \n" \
                        f"\n" \
                        f"To **spectate**, you don't have to do anything! Anyone can spectate " \
                        f"by simply being in the thread.\n" \
                        f"\n" \
                        f"@everyone mentions will be used to notify players of important game events. Players are " \
                        f"advised to make sure their notification settings for this server are __not__ set to " \
                        f"suppress @everyone mentions.\n" \
                        f"\n" \
                        f"If you're a spectator, you'll also be pinged by these " \
                        f"@everyone mentions. If that's a problem, you'll have to either suppress @everyone mentions " \
                        f"in your notification settings for this server or stop spectating and leave the thread.\n" \
                        f"\n" \
                        f"The Game Host can begin the game at any time with `/uno host start`. Once the game " \
                        f"has begun, no new players will be able to join."

        intro_embed = discord.Embed(title=f"Welcome to {posessive(self.host.name)} UNO game!",
                                    description=intro_message,
                                    color=support.Color.mint())

        settings_embed = discord.Embed(title="Game Settings", description=str(self.settings),
                                       color=support.Color.mint())

        self.lobby_intro_msg = await self.thread.send(embeds=[intro_embed, settings_embed])
        await self.lobby_intro_msg.pin()

    async def start_game(self):
        """
        Starts an UNO game.
        """
        self.is_joinable = False
        await self.thread.edit(name=f"{self.short_name} with {self.host.name}!")

        random.shuffle(self.players)

        with support.Assets.uno():
            start_lines = open("uno_start_lines.txt").readlines()

        msg = random.choice(start_lines).replace("\n", "") + "\n\n"

        msg += "In UNO, your goal is to be the first player to get rid of all your cards each round. " \
               "Once a player gets rid of all their cards, the round ends and that player is awarded points " \
               "based on the cards everyone else is still holding."

        if self.settings.points_to_win == 0:
            msg += "\n\nThis is a **zero-point** game, so **the first player to get rid of all their cards " \
                   "wins the entire game**."
        else:
            msg += f"\n\nFor this UNO game, the first player to reach **{self.settings.points_to_win} points** wins."

        msg += " You can view the cards you currently hold at any time with `/uno hand`. When it's your turn, " \
               "you can play a card with `/uno play` or draw one with `/uno draw`.\n" \
               "\n" \
               "You can view a range of information about this UNO game with `/uno status`, including the " \
               "current turn order and score leaderboard.\n" \
               "\n" \
               "Let's play!"

        embed = discord.Embed(title="Let's play UNO!", description=msg, color=support.Color.mint())

        with support.Assets.uno():
            uno_logo = discord.File("uno_logo.png", filename="uno_logo.png")
            embed.set_image(url="attachment://uno_logo.png")

            await self.thread.send(content="@everyone", embed=embed, file=uno_logo)

        await asyncio.sleep(3)

        await self.start_new_round()

    async def add_player(self, ctx: discord.ApplicationContext, user: discord.User, is_host=False):
        """
        Adds a player to a not-yet-started UNO game.

        :param ctx: An ApplicationContext object.
        :param user: The discord.User object corresponding to the player.
        :param is_host: Flags whether the player being added is also the Game Host. Defaults to False.
        """
        if user not in await self.thread.fetch_members():
            await self.thread.add_user(user)

        self.players.append(UnoPlayer(user=user, game=self))

        join_message_embed = discord.Embed(title="A new player has joined the game!",
                                           description=f"{user.mention} joined the game. Say hello!",
                                           color=support.Color.mint())

        await self.thread.send(embed=join_message_embed)

        if not is_host:
            msg = f"If you didn't mean to join, you can leave the game with `/uno leave`. You can leave at any time, " \
                  f"but if the game has already started, you won't be able to rejoin.\n" \
                  f"\n" \
                  f"Be advised that the Game Host, {self.host.mention}, can kick you at any time, " \
                  f"and if you go AFK mid-game, I'll have you automatically removed for inactivity. Please remember " \
                  f"to be courteous to your fellow players.\n" \
                  f"\n" \
                  f"Have fun!"

            embed = discord.Embed(title=f"Welcome to UNO, {user.name}!", description=msg,
                                  color=support.Color.mint())

            await ctx.respond(embed=embed, ephemeral=True)

    async def remove_player(self, player_node: dllistnode):
        """
        Removes a player from an UNO game.

        :param player_node: The dllistnode object corresponding to the player to be removed.
        """

        player: UnoPlayer = player_node.value

        embed = discord.Embed(title="A player has left the game.",
                              description=f"{player.user.mention} has left the game.",
                              color=support.Color.red())

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

    async def walk_players(self, player_node: dllistnode, steps: int, use_value=False) -> dllistnode or UnoPlayer:
        """
        Circularly traverse the list of a game's players.

        :param player_node: The node to start traversing from.
        :param steps: The number of steps to traverse.
        :param use_value: If True, return the value of the node (i.e. the UnoPlayer object) instead of the node itself.
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

    async def start_new_round(self):
        """
        Starts a new round of an UNO game.
        """
        self.current_round += 1
        self.reverse_turn_order = False
        self.color_in_play = ""
        self.suit_in_play = ""
        self.last_move = ""
        self.status.previous_turn_record.clear()

        for player in self.players.itervalues():
            # each player is dealt seven cards at the start of a round
            player.hand.clear()
            player.hand_value = 0
            await player.add_cards(7, dealing=True)

        msg = f"Round {self.current_round} has begun!"
        if self.current_round == 1:
            msg += " Seven cards have been dealt to each player. Check them out with `/uno hand`."
        else:
            msg += " Any cards you had at the end of the previous round have been taken, and seven new cards have " \
                   "been dealt to each player. Check them out with `/uno hand`."

        embed = discord.Embed(title=f"Round {self.current_round}: Start!", description=msg,
                              color=support.Color.mint())

        await self.thread.send(embed=embed)
        await self.start_next_turn()

    async def end_current_round(self, round_winner: UnoPlayer):
        """
        Ends the current round of an UNO game.
        """
        self.current_player = None

        # the number of points awarded to a round's winner is based on the point values of all cards held
        # by the other players at the end of a round
        awarded_points = sum([player.hand_value for player in self.players.itervalues()])

        round_winner.points += awarded_points

        winner_rank = self.status.get_player_ranking(round_winner)

        msg = f"Congratulations, {round_winner.user.mention}! You won Round {self.current_round}!\n" \
              f"\n" \
              f"Based on the cards everyone else is holding, {round_winner.user.name} has been awarded " \
              f"**{awarded_points} points**.\n" \
              f"\n" \
              f"{round_winner.user.name} currently has **{round_winner.points} points**, putting them in " \
              f"**{winner_rank} place**"

        if round_winner.points < self.settings.points_to_win:
            point_gap = self.settings.points_to_win - round_winner.points
            msg += f"—{self.settings.points_to_win - round_winner.points} point{'s' if point_gap > 1 else ''} " \
                   f"away from winning the game"

        msg += ". To view the full leaderboard, use `/uno status`."

        embed = discord.Embed(title=f"Round {self.current_round}: Over! {round_winner.user.name} Wins!",
                              description=msg,
                              color=support.Color.mint())

        await self.thread.send(content="@everyone", embed=embed)

        if round_winner.points >= self.settings.points_to_win:
            await self.end_game(game_winner=round_winner)
        else:
            await asyncio.sleep(5)
            await self.start_new_round()

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

        embed = discord.Embed(title="New Turn",
                              description=f"It's {posessive(self.current_player.value.user.name)} turn.",
                              color=support.Color.white())

        embed.set_thumbnail(url=self.current_player.value.user.display_avatar.url)

        await self.thread.send(content=f"{self.current_player.value.user.mention}, it's your turn.", embed=embed)
        await self.turn_timer()

    async def end_current_turn(self):
        """
        Ends the current player's turn.
        """
        if self.turn_record:
            await self.thread.send(embeds=self.turn_record)

        self.status.previous_turn_record = self.turn_record.copy()
        self.turn_record.clear()

        round_winner = discord.utils.find(lambda player: len(player.hand) == 0, self.players.itervalues())

        if round_winner:
            await self.end_current_round(round_winner=round_winner)
        else:
            await self.start_next_turn()

    async def end_game(self, game_winner: UnoPlayer):
        """
        Ends the game. This is only called when a player meets the win condition, and should not be confused
        with force closing the game.
        """
        self.__all_games__.pop(self.thread.id)

        msg = f"Congratulations, {game_winner.user.mention}! You won UNO!\n" \
              f"\n" \
              f"{game_winner.user.name} won the game with a total of **{game_winner.points} points**. To see " \
              f"the final leaderboard for this game, use the button below.\n" \
              f"\n" \
              f"This thread will be automatically deleted in 60 seconds. Thanks for playing!"

        embed = discord.Embed(title=f"UNO: Game Over! {game_winner.user.name} Wins!", description=msg,
                              color=support.Color.mint())
        embed.set_thumbnail(url=game_winner.user.display_avatar.url)
        await self.thread.edit(name=f"UNO with {self.host.name} - Game Over!")
        msg = await self.thread.send(content="@everyone", embed=embed, view=uno.UnoGameEndView(game=self))
        await msg.pin()

        await asyncio.sleep(60)
        await self.thread.delete()

    async def turn_timer(self):
        """
        Enforces a time limit on how long players can take to move.
        """
        # before the timer is set, the turn's unique identifier is recorded
        turn_uuid = self.turn_uuid

        # the game waits to give the player time to move
        await asyncio.sleep(self.settings.timeout)

        # if, after the timer is up, the uuid of the current turn is still the same as the one recorded
        # by the timer, the player times out
        if self.turn_uuid == turn_uuid and self.retrieve_game(self.thread.id) and self.current_player:
            player: UnoPlayer = self.current_player.value
            player.timeout_counter += 1

            # if *every* player times out consecutively, the game is force closed for inactivity
            if sum(player.timeout_counter for player in self.players.itervalues()) >= len(self.players):
                await self.force_close(reason="inactivity")

            # if the player has timed out for three turns in a row, they are removed from the game for inactivity
            elif player.timeout_counter == 3:
                embed = discord.Embed(title=f"{player.user.name} timed out.",
                                      description=f"{player.user.name} was removed from the game for inactivity.",
                                      color=support.Color.red())
                await self.thread.send(embed=embed)

                embed = discord.Embed(title=f"You timed out of {posessive(self.host.name)} UNO game.",
                                      description=f"You were removed from {self.host.name}'s UNO game in "
                                                  f"{self.guild.name} for inactivity.",
                                      color=support.Color.red())
                await player.user.send(embed=embed)

                await self.remove_player(self.current_player)

            # if neither of the above conditions are met, the player is forced to draw a card and forfeit their turn
            else:
                processor = UnoEventProcessor(self)
                await processor.turn_timeout_event(player=player)
                await player.end_turn()

    def is_card_playable(self, card: UnoCard):
        """
        Given an :class:`UnoCard`, this method determines whether it can be played on the current turn.
        """
        # a card is playable if it matches the color of the last card played...
        return (card.color.casefold() == self.color_in_play.casefold()
                # ...or the suit of the same.
                or card.suit.casefold() == self.suit_in_play.casefold()
                # wild cards are always playable
                or card.color is UnoCardColor.WILD
                # if there's no color in play (e.g. at the start of a round), all cards are playable
                or not self.color_in_play)

    async def kick_player(self, player_node: dllistnode):
        """
        Kicks a player from the game.

        :param player_node: The node of the player to kick.
        """
        embed = discord.Embed(title="Player Kicked",
                              description=f"{player_node.value.user.mention} has been kicked from the game.",
                              color=support.Color.red())

        await self.thread.send(embed=embed)
        await self.remove_player(player_node)

        embed = discord.Embed(title=f"You were kicked from {posessive(self.host.name)} UNO game.",
                              description=f"You were kicked from {self.host.name}'s UNO game in {self.guild.name}.",
                              color=support.Color.red())

        embed.timestamp = discord.utils.utcnow()

        await player_node.value.user.send(embed=embed)

    async def transfer_host(self, new_host: discord.User):
        """
        Transfers Game Host privileges from one user to another.

        :param new_host: The user to transfer host privileges to.
        """
        old_host = self.host
        self.host = new_host

        embed = discord.Embed(title="The Game Host has changed!",
                              description=f"{old_host.mention} has transferred host powers to {new_host.mention}. "
                                          f"{new_host.mention} is now the Game Host.",
                              color=support.Color.orange())

        await self.thread.send(content="@everyone", embed=embed)

        await self.thread.edit(name=self.thread.name.replace(old_host.name, new_host.name))

        intro = self.lobby_intro_msg
        intro_0 = intro.embeds[0]
        intro_0.title = intro_0.title.replace(old_host.name, new_host.name)
        intro_0.description = intro_0.description.replace(old_host.mention, new_host.mention)
        intro.embeds[0] = intro_0
        await self.lobby_intro_msg.edit(embeds=intro.embeds)


class UnoGameSettings:
    """
    Represents the settings for an UNO game.
    """

    def __init__(self, max_players, points_to_win, timeout):
        """
        The constructor for ``UnoGameSettings``.

        :param max_players: The maximum number of players allowed to join the game.
        :param points_to_win: The number of points required to win the game.
        :param timeout: The number of seconds within which players must complete their turns.
        """
        self.max_players = max_players
        self.points_to_win = points_to_win
        self.timeout = timeout

    def __str__(self):
        players_str = f"__**Maximum Players**: {self.max_players}__\n" \
                      f"Up to {self.max_players} players can join this UNO game. Once that quota is filled, " \
                      f"no one else will be able to join unless a player leaves or is removed by the Game Host."

        points_str = f"__**Points to Win**: {self.points_to_win}__\n"
        if self.points_to_win == 0:
            points_str += "The first player to get rid of all their cards will win the game."
        else:
            points_str += f"The first player to reach {self.points_to_win} points will win the game."

        timeout_str = f"__**Timeout**: {self.timeout} seconds__\n" \
                      f"Each player will have {self.timeout} seconds to move during their turn. If a player exceeds " \
                      f"this time limit, they will be forced to draw a card and forfeit their turn."

        return "\n\n".join([players_str, points_str, timeout_str])


class UnoPlayer:
    """
    Represents a player in an UNO game.
    """

    def __init__(self, user: discord.User, game: UnoGame):
        """
        The constructor for ``UnoPlayer``.

        :param user: The discord.User object corresponding to the player.
        :param game: The UnoGame object representing the game the player is part of.

        Other attributes:
        - ``points``: The number of points the player has.
        - ``hand``: A list of cards in the player's hand. This is sorted by card color (R, G, B, Y, W) and then by
        suit (0-9, Draw Two, Skip, Reverse).
        - ``can_say_uno``: Whether or not the player can say UNO.
        - ``has_said_uno``: Whether or not the player has said UNO.
        - ``terminable_views``: A list of :class:``discord.ui.View`` objects that must be automatically stopped when
        the player's turn ends.
        - ``timeout_counter``: The number of consecutive times the player has timed out.
        - ``num_cards_played``: The total number of cards the player has played.
        - ``num_cards_drawn``: The total number of cards the player has drawn.
        """
        self.user = user
        self.game = game

        self.points: int = 0
        self.hand = SortedKeyList(
            key=lambda card: [(string.digits + "rbgyw" + string.printable).index(char) for char in str(card).casefold()]
        )
        self.hand_value: int = 0
        self.can_say_uno = False
        self.has_said_uno = False
        self.terminable_views: list[support.EnhancedView] = []
        self.timeout_counter: int = 0

        # for uno status center
        self.num_cards_played = 0
        self.num_cards_drawn = 0

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
                            f"{chr(10).join([f'- {str(card)} {card.emoji()}' for card in page])}",
                color=support.Color.mint()
            )
            for page in split_cards]

        for embed in pages:
            embed.set_footer(text=discord.utils.remove_markdown(self.game.last_move))

        paginator = discord_pages.Paginator(pages=pages, use_default_buttons=False,
                                            custom_buttons=support.paginator_emoji_buttons())

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
                msg = f"If you play this card, you'll only have one card left.\n" \
                      f"\n" \
                      f"When you have only one card left, you must use `/uno uno` to say 'UNO!' and alert the other " \
                      f"players of this fact. If another player believes you have only one card left and haven't " \
                      f"said 'UNO!', they can use `/uno callout` and force you to draw two cards as punishment.\n" \
                      f"\n" \
                      f"You can use `/uno uno` at any time, provided you only have one card and haven't been " \
                      f"called out.\n" \
                      f"\n" \
                      f"Proceed with playing this card?"
                embed = discord.Embed(title="One Card Remaining", description=msg,
                                      color=support.Color.orange())

                view = uno.UnoTerminableConfView(ctx=ctx)
                confirmation = await view.request_confirmation(prompt_embeds=[embed], ephemeral=True, edit=True)

                if confirmation:
                    if not selected_card.color.casefold() == "wild":
                        await ctx.interaction.edit_original_message(content="Good luck! 🤞🏾", embeds=[], view=None)
                else:
                    await ctx.interaction.edit_original_message(content="Okay! Make your move whenever you're ready.",
                                                                embeds=[], view=None)

                    return

            # present color selection view if the player selects a wild card, provided it isn't the last card in
            # their hand
            if selected_card.color.casefold() == "wild" and len(self.hand) > 1:
                view = uno.WildColorSelectView(ctx=ctx, player=self)
                color_was_changed: bool = await view.choose_color()

                if color_was_changed:
                    # only play the card if the player selected a color
                    await self.play_card(selected_card)
            else:
                await self.play_card(selected_card)

    async def play_card(self, card: UnoCard, with_draw: bool = False):
        """
        Plays UNO cards.

        :param card: The card to play.
        :param with_draw: Whether or not the card with automatically played after being drawn.
        """
        await self.reset_timeouts()

        # remove the card from the player's hand and update their hand value accordingly
        self.hand.remove(card)
        await self.update_hand_value(card, use_subtraction=True)
        self.num_cards_played += 1

        processor = UnoEventProcessor(self.game)
        await processor.card_played_event(player=self, card=card, with_draw=with_draw)

        if card.color.casefold() == UnoCardColor.WILD:
            await processor.wild_event(player=self)

        if card.suit.casefold() == "draw two":
            await processor.draw_two_event()
        elif card.suit.casefold() == "draw four":
            await processor.draw_four_event()
        elif card.suit.casefold() == "skip":
            await processor.skip_event()
        elif card.suit.casefold() == "reverse":
            await processor.reverse_event()

        await self.end_turn()

    async def draw_card(self, ctx: discord.ApplicationContext):
        """
        Draws an UNO card.

        :param ctx: A discord.ApplicationContext object.
        """

        view = uno.UnoDrawCardView(ctx=ctx)
        await view.draw_card()

        if view.success:
            await self.reset_timeouts()

            drawn_card = await self.add_cards(1, return_added_cards=True)

            card = drawn_card[0]

            if view.autoplay and self.game.is_card_playable(card) and card.color.casefold() != "wild":
                # play the card if it can be played on the current turn and isn't a wild or wild draw four
                embed = discord.Embed(title="Card Drawn and Played",
                                      description=f"You drew and played a **{str(card)}**.",
                                      color=card.embed_color())
                embed.set_thumbnail(url=card.emoji().url)

                await ctx.interaction.edit_original_message(embeds=[embed], view=None)

                if len(self.hand) - 1 == 1:
                    embed = discord.Embed(title="One Card Remaining",
                                          description="You'll need to say 'UNO!' or risk being called out by "
                                                      "another player.",
                                          color=support.Color.orange())

                    await ctx.interaction.followup.send(embed=embed, ephemeral=True)

                await self.play_card(card, with_draw=True)
            else:
                embed = discord.Embed(title="Card Drawn", description=f"You drew a **{str(card)}**.",
                                      color=card.embed_color())
                embed.set_thumbnail(url=card.emoji().url)

                await ctx.interaction.edit_original_message(embeds=[embed], view=None)

                processor = UnoEventProcessor(self.game)
                await processor.card_drawn_event(player=self)

                await self.end_turn()
        elif view.success is False:
            msg = "Okay! Make your move whenever you're ready."
            await ctx.interaction.edit_original_message(content=msg, embeds=[], view=None)

    async def say_uno(self):
        """
        Says 'UNO!' on behalf of the invoking player.
        """
        processor = UnoEventProcessor(self.game)
        await processor.say_uno_event(player=self)

    async def callout(self, ctx: discord.ApplicationContext, recipient: uno.UnoPlayer):
        """
        Calls out a player for having one remaining card and failing to say 'UNO!'.

        :param ctx: A discord.ApplicationContext object.
        :param recipient: The player being called out.
        """
        msg = f"If you think {recipient.user.name} has one card left and hasn't said 'UNO!', you can call them " \
              f"out.\n" \
              f"\n" \
              f"If the callout **succeeds** (meaning {recipient.user.name} actually has one card left and hasn't " \
              f"said 'UNO!'), {recipient.user.name} will draw two cards.\n" \
              f"\n" \
              f"If the callout **fails** (meaning {recipient.user.name} has said 'UNO!' or has more than " \
              f"one card), you will draw a card and **your turn will end**.\n" \
              f"\n" \
              f"Call out {recipient.user.name}?"

        embed = discord.Embed(title=f"Call out {recipient.user.name}?", description=msg,
                              color=support.Color.orange())

        view = uno.UnoTerminableConfView(ctx=ctx)
        confirmation = await view.request_confirmation(prompt_embeds=[embed], ephemeral=True)

        if confirmation:
            processor = UnoEventProcessor(self.game)

            if recipient.can_say_uno and not recipient.has_said_uno:
                embed = discord.Embed(title="The callout was successful!",
                                      description=f"{recipient.user.name} will draw two cards.",
                                      color=support.Color.green())

                await ctx.interaction.edit_original_message(embeds=[embed], view=None)
                await processor.callout_event(challenger=self, recipient=recipient, callout_success=True)
            else:
                embed = discord.Embed(title="The callout failed.",
                                      description="You'll draw a card, and your turn will end.",
                                      color=support.Color.brand_red())

                await ctx.interaction.edit_original_message(embeds=[embed], view=None)
                await processor.callout_event(challenger=self, recipient=recipient, callout_success=False)
                await self.end_turn()
        else:
            await ctx.interaction.edit_original_message(content="Okay! Make your move whenever you're ready.",
                                                        embeds=[], view=None)

    async def add_cards(self, num_cards, dealing=False, return_added_cards=False):
        """
        Adds cards to the player's hand. This method is the only means by which cards are added to a player's hand,
        whether by dealing or drawing.

        :param num_cards: The number of cards to add.
        :param dealing: Indiciates whether the cards are being added by dealing.
        :param return_added_cards: If True, this method will return a list of the cards that were added.
        """
        new_cards = UnoCard.generate_cards(num_cards)

        for card in new_cards:
            await self.update_hand_value(card)

        if not dealing:
            self.num_cards_drawn += num_cards

        self.hand.update(new_cards)

        self.can_say_uno = False
        self.has_said_uno = False

        if return_added_cards:
            return new_cards

    async def update_hand_value(self, card: UnoCard, use_subtraction=False):
        """
        Updates the point value of a player's hand whenever a card is added to or removed from it.

        :param card: The card with which to update the player's hand value.
        :param use_subtraction: If True, the point value of the card is subtracted from the player's hand value
        instead of added to it.
        """
        if use_subtraction:
            self.hand_value -= card.point_value()
        else:
            self.hand_value += card.point_value()

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

        await self.game.end_current_turn()

        self.terminable_views.clear()

    def __str__(self):
        return self.user.name


class _UnoCardEnum(Enum):
    def title(self):
        return str(self).title()

    def casefold(self):
        return str(self).casefold()

    def emoji_key(self):
        return self.name.lower()

    def __str__(self):
        return self.value


class _UnoCardColorMeta(EnumMeta):
    def __iter__(self):
        for color in super().__iter__():
            if color is not UnoCardColor.WILD:
                yield color


class _UnoCardSuitMeta(EnumMeta):
    def __iter__(self):
        for suit in super().__iter__():
            if suit not in [UnoCardSuit.DRAW_FOUR, UnoCardSuit.NONE]:
                yield suit


class UnoCardColor(_UnoCardEnum, metaclass=_UnoCardColorMeta):
    """
    Enumerates UNO card colors.

    Notes
    -----
    - WILD is excluded from this enumeration's iterator.
    """
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    WILD = "wild"


class UnoCardSuit(_UnoCardEnum, metaclass=_UnoCardSuitMeta):
    """
    Enumerates UNO card suits.

    Notes
    -----
    - DRAW_FOUR and NONE are excluded from this enumeration's iterator as they can only appear on cards of
      color :class:`UnoCardColor.WILD`. The former is reserved for the Wild Draw Four card (which is the only card of that
      suit) and the latter for the suitless Wild card.
    """
    REVERSE = "reverse"
    SKIP = "skip"
    DRAW_TWO = "draw two"
    DRAW_FOUR = "draw four"
    NONE = ""
    ZERO, ONE, TWO, THREE, FOUR, FIVE, SIX, SEVEN, EIGHT, NINE = list(string.digits)


class UnoCard:
    """
    An UNO card.

    Parameters
    ----------
    color: :class:`UnoCardColor`
        The color of the card.
    suit: :class:`UnoCardSuit`
        The suit of the card.

    Attributes
    ----------
    uuid: :class:`uuid.UUID`
        The card's randomly-generated unique identifier.
    """

    def __init__(self, color: UnoCardColor, suit: UnoCardSuit = UnoCardSuit.NONE):
        self.color = color
        self.suit = suit

        self.uuid = None

    @classmethod
    def generate_cards(cls, num_cards) -> list[UnoCard]:
        """
        Gemerate UNO cards.

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
        - This algorithm has an equal chance of generating any one of the 54 distinct UNO cards in a standard deck.
          This does not emulate the probability of drawing cards in the canonical implementation of UNO, in which
          cards appear with varying frequencies.
        """
        all_cards = [cls(color, suit) for color in UnoCardColor for suit in UnoCardSuit]
        all_cards.extend([cls(UnoCardColor.WILD), cls(UnoCardColor.WILD, UnoCardSuit.DRAW_FOUR)])

        cards_to_return = []
        for i in range(num_cards):
            card = copy.copy(random.choice(all_cards))
            card.uuid = str(uuid.uuid4())
            cards_to_return.append(card)

        return cards_to_return

    def emoji(self) -> discord.PartialEmoji:
        """
        Get the card's corresponding Discord emoji.
        """
        with support.Assets.uno():
            card_emoji = toml.load(open("uno_card_emotes.toml"))
            return discord.PartialEmoji.from_str(card_emoji[self.color.emoji_key()][self.suit.emoji_key()])

    def point_value(self) -> int:
        """
        Get the point value of an UNO card.
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

    def embed_color(self):
        """
        Get the embed color associated with the card.
        """

        embed_colors = {
            "red": support.Color.brand_red(),
            "blue": support.Color.blue(),
            "green": support.Color.green(),
            "yellow": support.Color.yellow(),
            "wild": support.Color.black(),
        }

        return embed_colors[self.color.casefold()]

    def __str__(self):
        if self.suit:
            return f"{self.color.title()} {self.suit.title()}"
        else:
            return self.color


class UnoEventProcessor:
    """
    Processes game events.
    """

    def __init__(self, game: UnoGame):
        self.game = game

    async def card_played_event(self, player: UnoPlayer, card: UnoCard, with_draw: bool = False):
        """
        The handler for the event of playing a card.

        :param player: The player who played the card.
        :param card: The card that was played.
        :param with_draw: Whether or not the card was automatically played after being drawn.
        """
        if card.color.casefold() != "wild":
            self.game.color_in_play = card.color

        self.game.suit_in_play = card.suit

        embed = discord.Embed(title=f"Card {'Drawn and ' if with_draw else ''}Played",
                              description=f"**{player.user.name}** {'draws and' if with_draw else ''} "
                                          f"plays a **{str(card)}**.",
                              color=card.embed_color())

        embed.set_thumbnail(url=card.emoji().url)
        embed.set_footer(icon_url=player.user.display_avatar.url,
                         text=f"{player.user} • UNO with {self.game.host.name}! • Round {self.game.current_round}")

        self.game.last_move = "The last card played was a "

        if card.color.casefold() == "wild":
            if card.suit.casefold() == "draw four":
                self.game.last_move += "**Wild Draw Four**. "
            else:
                self.game.last_move += f"**Wild**. "

            self.game.last_move += f"The current color in play is **{self.game.color_in_play.title()}**."
        else:
            self.game.last_move += f"**{card.color.title()} {card.suit.title()}**."

        self.game.turn_record.append(embed)

    async def card_drawn_event(self, player: UnoPlayer):
        """
        The handler for the event of drawing a card.

        :param player: The player who drew the card.
        """
        embed = discord.Embed(title="Card Drawn", description=f"**{player.user.name}** draws a card.",
                              color=support.Color.greyple())

        embed.set_thumbnail(url=player.user.display_avatar.url)
        embed.set_footer(icon_url=player.user.display_avatar.url,
                         text=f"{player.user} • UNO with {self.game.host.name}! • Round {self.game.current_round}")

        self.game.turn_record.append(embed)

    async def draw_two_event(self):
        """
        The handler for the event of a Draw Two card being played.
        """
        self.game.skip_next_player = True

        next_player: UnoPlayer = await self.game.walk_players(self.game.current_player, 1, use_value=True)
        await next_player.add_cards(2)

        self.game.turn_record[-1].add_field(name="🎬 Take Two!",
                                            value=f"**{next_player.user.name}** draws two cards and "
                                                  f"forfeits their turn.",
                                            inline=False)

    async def draw_four_event(self):
        """
        The handler for the event of a Draw Four card being played. The only card with this suit is the Wild Draw Four
        card, so a ``wild_event()`` will always accompany this event.
        """
        self.game.skip_next_player = True

        next_player: UnoPlayer = await self.game.walk_players(self.game.current_player, 1, use_value=True)
        await next_player.add_cards(4)

        self.game.turn_record[-1].add_field(name="🍀 Four Score!",
                                            value=f"**{next_player.user.name}** draws four cards and "
                                                  f"forfeits their turn.",
                                            inline=False)

    async def skip_event(self):
        """
        The handler for the event of a Skip card being played.
        """
        self.game.skip_next_player = True

        skipped_player = await self.game.walk_players(self.game.current_player, 1, use_value=True)

        self.game.turn_record[-1].add_field(name="⏩ Fast Forward!",
                                            value=f"**{posessive(skipped_player.user.name)}** turn is skipped.",
                                            inline=False)

    async def reverse_event(self):
        """
        The handler for the event of a Reverse card being played.
        """
        self.game.reverse_turn_order = not self.game.reverse_turn_order

        if len(self.game.players) == 2:
            self.game.skip_next_player = True

        self.game.turn_record[-1].add_field(name="🔄 Reverse, Reverse!", value="The turn order is reversed.",
                                            inline=False)

    async def wild_event(self, player: UnoPlayer):
        """
        The handler for the event of a Wild card being played.

        :param player: The player who played the Wild card.
        """

        self.game.turn_record[-1].add_field(name="🎲 A Wild card appears!",
                                            value=f"**{player.user.name}** changes the color in play to "
                                                  f"**{self.game.color_in_play.title()}**.",
                                            inline=False)

    async def say_uno_event(self, player: UnoPlayer):
        """
        The handler for the event of a a player saying 'UNO!'.

        :param player: The player saying 'UNO!'.
        """
        player.can_say_uno = False
        player.has_said_uno = True

        embed = discord.Embed(title=f"{player.user.name} says UNO!",
                              description=f"**{player.user.mention}** has one card left.",
                              color=support.Color.orange())

        await self.game.thread.send(content="@everyone", embed=embed)

    async def turn_timeout_event(self, player: UnoPlayer):
        """
        The handler for the event of a player's turn timing out.

        :param player: The player whose turn timed out.
        """
        await player.add_cards(1)

        embed = discord.Embed(title=f"{player.user.name} timed out.",
                              description=f"{player.user.mention} took too long to move and was forced to draw a card.",
                              color=support.Color.red())

        self.game.turn_record.append(embed)

    async def callout_event(self, challenger: UnoPlayer, recipient: UnoPlayer, callout_success: bool):
        """
        The handler for the event of a player calling out another player.

        :param challenger: The player issuing the callout.
        :param recipient: The player receiving the callout.
        :param callout_success: Whether or not the callout was successful.
        """
        msg = f"{challenger.user.name} calls out {recipient.user.name} for having one card left and failing to say " \
              f"'UNO!'."

        if callout_success:
            await recipient.add_cards(2)

            msg += f"\n\n**The callout succeeds!** {recipient.user.name} draws two cards.\n" \
                   f"\n" \
                   f"It's still {challenger.user.mention}'s turn."

            embed = discord.Embed(title=f"📢 {challenger.user.name} calls out {recipient.user.name}!",
                                  description=msg,
                                  color=support.Color.nitro_pink())

            await self.game.thread.send(embed=embed)
        else:
            await challenger.add_cards(1)

            msg += f"\n\n**The callout fails!** {challenger.user.name} draws a card and forfeits their turn."

            embed = discord.Embed(title=f"📢 {challenger.user.name} calls out {recipient.user.name}!",
                                  description=msg,
                                  color=support.Color.nitro_pink())

            self.game.turn_record.append(embed)


class UnoStatusCenter:
    """
    The backend of the UNO Status Center. (The frontend is :class:`uno.views.UnoStatusCenterView`.)
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

    def get_player_list(self) -> list[UnoPlayer]:
        """
        Returns a list of all players in the game. The first player will always be the game host,
        followed by the rest of the players in non-reversed turn order.
        """
        return reversed(SortedKeyList(self.game.players.itervalues(), key=lambda p: p.user == self.game.host))

    def get_turn_order(self):
        """
        Returns a list of all players in the game in turn order. The output of this method is affected
        by whether the turn order is reversed or not. The turn order is randomized at the start of each game,
        and is not necessarily the same as the order in which players joined the game.
        """
        if self.game.reverse_turn_order:
            return reversed([*self.game.players.itervalues()])
        else:
            return self.game.players.itervalues()

    def get_last_turn(self) -> list[discord.Embed]:
        """
        Returns a list of :class:`discord.Embed` objects representing the events of the previous turn.
        """
        return self.previous_turn_record

    def get_leaderboard(self) -> list[list[UnoPlayer]]:
        """
        Returns a list of all players in the game, sorted in descending order by score. To be more precise,
        this method returns a list of lists of :class:`UnoPlayer` objects - players who have the same score
        are grouped together in the same sub-list.
        """
        point_order = reversed(SortedKeyList(self.game.players.itervalues(), key=lambda p: p.points))

        leaderboard = []
        determinant = 0
        for player in point_order:
            if not leaderboard:
                determinant = player.points
                leaderboard.append([player])
            elif player.points == determinant:
                leaderboard[-1].append(player)
            elif player.points < determinant:
                determinant = player.points
                leaderboard.append([player])

        return leaderboard

    def get_player_ranking(self, player, with_string=False) -> str:
        """
        Returns a string representation of the player's ranking in the game. (e.g. "1st", "2nd", "3rd", etc.).

        :param player: The player whose ranking to return.
        :param with_string: If True, the method will return the full ranking string in the
        format "Xth of Y (tied with Z others)".
        """
        leaderboard_group = discord.utils.find(lambda group: player in group, self.get_leaderboard())
        ranking = inflect.ordinal(self.get_leaderboard().index(leaderboard_group) + 1)

        if with_string:
            ranking += f" of {len(self.game.players)}"
            ties = len(leaderboard_group) - 1

            if ties > 0:
                ranking += f" (tied with {ties} {inflect.plural('other', ties)})"

        return ranking

    def get_player_stats(self, player: UnoPlayer) -> dict:
        """
        Returns a dictionary of statistics for the given player.
        """
        return {
            "Rank": self.get_player_ranking(player, with_string=True),
            "Points": player.points,
            "Cards Held": len(player.hand),
            "Hand Value": player.hand_value,
            "Cards Played": player.num_cards_played,
            "Cards Drawn": player.num_cards_drawn,
        }
