from __future__ import annotations

import asyncio
import json
import os.path
import random
import uuid
from typing import Union, TypedDict

import discord
import llist
from llist import dllist as DoublyLinkedList

import support
from cogs import uno


class UnoGame:
    """
    Represents an UNO game.
    """
    __all_games__ = dict()

    def __init__(self,
                 guild: discord.Guild,
                 thread: discord.Thread,
                 host: discord.User,
                 max_players: int,
                 points_to_win: int):
        """
        The constructor for ``UnoGame``.

        :param guild: The server (a.k.a. "guild") in which the game is taking place.
        :param thread: The game's associated thread.
        :param host: The user who is the Game Host.
        :param max_players: The maximum number of players permitted to join the game.
        :param points_to_win: The number of points required to win the game.
        """
        self.guild = guild
        self.thread = thread
        self.host = host
        self.max_players = max_players
        self.points_to_win = points_to_win

        self.players = DoublyLinkedList()
        self.is_joinable = True
        self.current_round = 0
        self.current_player = None
        self.last_move = None
        self.color_in_play = None
        self.attribute_in_play = None
        self.turn_record = []

        self.__all_games__[self.thread.id] = self

    @classmethod
    def retrieve_game(cls, thread_id) -> Union[UnoGame, None]:
        """
        Retrieves an UnoGame object given the unique identifier of its associated game thread.

        :param thread_id: The unique identifier of the game's associated thread.
        :return: The UnoGame object associated with the passed-in thread ID if one exists; otherwise None.
        """
        return cls.__all_games__.get(thread_id)

    @classmethod
    def get_hosted_games(cls, user: discord.User, guild_id: int) -> Union[UnoGame, None]:
        """
        Retrieves an ``UnoGame`` objects where the Game Host is a particular user and that are taking places in a
        particular server.

        :param user: The Game Host to look for.
        :param guild_id: The unique identifier of the server to look for.
        :return: An ``UnoGame`` object associated with the specified Game Host and server if one exists; otherwise None.
        """
        return next((game for game in cls.__all_games__.values() if
                     game.host == user and game.guild.id == guild_id),
                    None)

    @classmethod
    async def force_close_channel_deletion(cls, game: UnoGame):
        """
        Force closes an UNO game in the event that the parent channel of its associated thread is deleted.

        :param game: The UNO game to close.
        """
        cls.__all_games__.pop(game.thread.id)

        msg = f"Your UNO game in {game.guild.name} was forced to end because the parent channel of its game " \
              f"thread was deleted."
        embed = discord.Embed(title="Your UNO game was forced to end.", description=msg,
                              color=support.ExtendedColors.red(), timestamp=discord.utils.utcnow())

        await game.host.send(embed=embed)

    @classmethod
    async def force_close_thread_deletion(cls, game: UnoGame):
        """
        Force closes an UNO game in the event that its associated thread is deleted.

        :param game: The UNO game to close.
        """
        cls.__all_games__.pop(game.thread.id)

        msg = f"Your UNO game in {game.guild.name} was forced to end because its game thread was deleted."
        embed = discord.Embed(title="Your UNO game was forced to end.", description=msg,
                              color=support.ExtendedColors.red(), timestamp=discord.utils.utcnow())

        await game.host.send(embed=embed)

    @classmethod
    async def force_close_host_left(cls, game: UnoGame):
        """
        Force closes an UNO game in the event that the Game Host leaves its associated thread.

        :param game: The UNO game to close.
        """
        cls.__all_games__.pop(game.thread.id)

        thread_msg = f"This UNO game was forced to end because the Game Host, {game.host.mention}, " \
                     f"left.\n" \
                     f"\n" \
                     f"This thread has been locked and will be automatically deleted in two minutes."
        thread_embed = discord.Embed(title="This UNO game was forced to end.", description=thread_msg,
                                     color=support.ExtendedColors.red(), timestamp=discord.utils.utcnow())

        host_msg = f"Your UNO game in {game.guild.name} was forced to end because you left either the game " \
                   f"or its associated thread."
        host_embed = discord.Embed(title="Your UNO game was forced to end.", description=host_msg,
                                   color=support.ExtendedColors.red(), timestamp=discord.utils.utcnow())

        await game.thread.edit(name=f"UNO with {game.host.name} - Game Over!")
        msg = await game.thread.send(embed=thread_embed)
        await msg.pin()
        await game.thread.archive(locked=True)

        await game.host.send(embed=host_embed)

        await asyncio.sleep(120)

        await game.thread.delete()

    @classmethod
    async def force_close_all_players_left(cls, game: UnoGame):
        """
        Force closes an UNO game in the event that all players aside from the Game Host leave the game.

        :param game: The UNO game to close.
        """
        cls.__all_games__.pop(game.thread.id)

        thread_msg = f"This UNO game was forced to end because all players left.\n" \
                     f"\n" \
                     f"This thread has been locked and will be automatically deleted in two minutes."
        thread_embed = discord.Embed(title="This UNO game was forced to end.", description=thread_msg,
                                     color=support.ExtendedColors.red(), timestamp=discord.utils.utcnow())

        host_msg = f"Your UNO game in {game.guild.name} was forced to end because all other players left."
        host_embed = discord.Embed(title="Your UNO game was forced to end.", description=host_msg,
                                   color=support.ExtendedColors.red(), timestamp=discord.utils.utcnow())

        await game.thread.edit(name=f"UNO with {game.host.name} - Game Over!")
        msg = await game.thread.send(embed=thread_embed)
        await msg.pin()
        await game.thread.archive(locked=True)

        await game.host.send(embed=host_embed)

        await asyncio.sleep(120)

        await game.thread.delete()

    async def retrieve_player(self, user: discord.User) -> UnoPlayer:
        """
        Retrieves a player from ``UnoGame().players`` given that player's user object.

        :param user: The discord.User object corresponding to the player.
        :return: A dllistnode object representing the player.
        """
        return next(player for player in self.players.itervalues() if player.user.id == user.id)

    async def waiting_room_intro(self):
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
                        "\n" \
                        f"Up to **{self.max_players}** players can join this UNO game. When that quota is filled, " \
                        f"no one else will be able to join the game unless a player leaves or is removed by " \
                        f"the Game Host.\n" \
                        f"\n" \
                        f"The Game Host can begin the game at any time with `/uno gamehost start`. Once the game " \
                        f"has begun, no new players will be able to join."

        intro_embed = discord.Embed(title=f"Welcome to {self.host.name}'s UNO game!", description=intro_message,
                                    color=support.ExtendedColors.mint())

        msg = await self.thread.send(embed=intro_embed)
        await msg.pin()

    async def host_start_game(self):
        self.is_joinable = False
        await self.thread.edit(name=f"UNO with {self.host.name}!")

        # noinspection PyTypeChecker
        random.shuffle(self.players)

        start_lines = open(os.path.join(os.getcwd(), "cogs/uno/files/uno_start_lines.txt")).readlines()

        start_msg = random.choice(start_lines).replace("\n", "") + "\n\n"

        start_msg += "In UNO, your goal is to be the first player to get rid of all your cards each round. " \
                     "Once a player gets rid of all their cards, the round ends and that player is awarded points " \
                     "based on the cards everyone else is still holding. For this UNO game, the first player " \
                     f"to reach **{self.points_to_win}** points wins.\n" \
                     "\n" \
                     "You can view the cards you currently hold at any time with `/uno hand`. When it's your turn, " \
                     "you can play a card with `/uno play` or draw one with `/uno draw`.\n" \
                     "\n" \
                     "You can view a range of information about this UNO game with `/uno status`, including the " \
                     "current turn order and score leaderboard.\n" \
                     "\n" \
                     "New to UNO, or just need a refresher? Learn everything you need to know about how to play with " \
                     "`/uno help`.\n" \
                     "\n" \
                     "Let's play!"

        start_embed = discord.Embed(title="Let's play UNO!", description=start_msg, color=support.ExtendedColors.mint())
        await self.thread.send(content="@everyone", embed=start_embed)

        await self.start_new_round()

    async def host_abort_game(self):
        """
        Aborts an UNO game. This function is called whenever an UNO Game Host invokes the
        ``/uno gamehost abort`` slash command.
        """
        UnoGame.__all_games__.pop(self.thread.id)

        thread_msg = f"The Game Host, {self.host.mention}, has ended this UNO game.\n" \
                     f"\n" \
                     f"This thread has been locked and will be automatically deleted in two minutes."
        thread_embed = discord.Embed(title="The Game Host has ended this UNO game.", description=thread_msg,
                                     color=support.ExtendedColors.red(), timestamp=discord.utils.utcnow())

        await self.thread.edit(name=f"UNO with {self.host.name} - Game Over!")
        msg = await self.thread.send(embed=thread_embed)
        await msg.pin()
        await self.thread.archive(locked=True)

        await asyncio.sleep(120)

        await self.thread.delete()

    async def add_player(self, ctx: discord.ApplicationContext, user: discord.User, is_host=False):
        """
        Adds a player to a not-yet-started UNO game.

        :param ctx: An ApplicationContext object.
        :param user: The discord.User object corresponding to the player.
        :param is_host: Flags whether the player being added is also the Game Host. Defaults to False.
        """
        if user not in await self.thread.fetch_members():
            await self.thread.add_user(user)

        self.players.append(UnoPlayer(user, self))

        join_message_embed = discord.Embed(title="A new player has joined the game!",
                                           description=f"{user.mention} joined the game. Say hello!",
                                           color=support.ExtendedColors.mint())

        await self.thread.send(embed=join_message_embed)

        if not is_host:
            ephemeral_join_msg = "If you're new to UNO, read up on how to play with `/help uno`. If you're not new " \
                                 "to UNO, you're still advised to check out `/help uno`, as some of the game's " \
                                 "rules deviate from the standard UNO ruleset.\n" \
                                 "\n" \
                                 "If you didn't mean to join, you can leave the game with `/uno leave.` You can " \
                                 "leave the game at any time, but if the game has already started, you won't be " \
                                 "able to rejoin.\n" \
                                 "\n" \
                                 f"The Game Host, {self.host.mention}, has the power to remove you from this game " \
                                 f"at any time. Furthermore, you may be automatically removed by me, " \
                                 f"<@939972078323519488>, in case of inactivity. If you're going AFK, be courteous " \
                                 f"to your fellow players and leave the game voluntarily first.\n" \
                                 f"\n" \
                                 f"Have fun!"

            ephemeral_join_embed = discord.Embed(title="Welcome to UNO!", description=ephemeral_join_msg,
                                                 color=support.ExtendedColors.mint())

            await ctx.respond(embed=ephemeral_join_embed, ephemeral=True)

    async def remove_player(self, player_node: llist.dllistnode):
        """
        Removes a player from an UNO game.

        :param player_node: The dllistnode object corresponding to the player to be removed.
        """
        player = player_node.value
        self.players.remove(player_node)

        leave_message_embed = discord.Embed(title="A player has left the game.", description=f"{player.user.mention} "
                                                                                             f"has left the game.",
                                            color=support.ExtendedColors.red())

        await self.thread.send(embed=leave_message_embed)

        if player.user == self.host:
            await UnoGame.force_close_host_left(self)

        elif len(self.players) <= 1 and not self.is_joinable:
            await UnoGame.force_close_all_players_left(self)

    async def start_new_round(self):
        self.current_round += 1
        self.current_player = None
        self.color_in_play = None
        self.attribute_in_play = None

        for player in self.players.itervalues():
            player.hand.clear()
            player.hand.extend(UnoCard.generate_cards(7))

        msg = f"Round {self.current_round} has begun!"
        if self.current_round == 1:
            msg += " Seven cards have been dealt to each player. Check them out with `/uno hand`."
        else:
            msg += " Any cards you had at the end of the previous round have been taken, and seven new cards have " \
                   "been dealt to each player. Check them out with `/uno hand`."

        embed = discord.Embed(title=f"Round {self.current_round}: Start!", description=msg,
                              color=support.ExtendedColors.mint())

        await self.thread.send(embed=embed)
        await self.start_next_turn()

    async def start_next_turn(self):
        if self.current_player is None or self.current_player.next is None:
            self.current_player = self.players.first
        else:
            self.current_player = self.current_player.next

        await self.thread.send(f"{self.current_player.value.user.mention}, it's your turn.")

    async def end_current_turn(self):
        if self.turn_record:
            await self.thread.send(embeds=self.turn_record)
        self.turn_record.clear()
        await self.start_next_turn()

    def verify_card_playability(self, card: UnoCard):
        return (card.color == self.color_in_play or card.attribute == self.attribute_in_play) \
               or self.color_in_play is None

    async def transfer_host(self, new_host):
        pass

    async def kick_from_thread(self, user: discord.User):
        pass


class UnoPlayer:
    """
    Represents a player in an UNO game.
    """

    def __init__(self, user: discord.User, game: UnoGame):
        """
        The constructor for ``UnoPlayer``.

        :param user: The discord.User object corresponding to the player.
        :param game: The UnoGame object representing the game the player is part of.
        """
        self.user = user
        self.game = game

        self.player_id = self.user.id
        self.hand: list[dict[str, UnoCard]] = []
        self.wd4_buffer = []
        self.can_challenge_wd4 = False
        self.receivable_challenges = {"uno": False, "wd4": False}

    async def show_hand(self, ctx: discord.ApplicationContext):
        msg = "Here are all the cards you're currently holding:\n\n"
        msg += "\n".join([f"- {card['card'].__str__()} {card['card'].emoji}" for card in self.hand])

        embed = discord.Embed(title="Your Hand", description=msg, color=support.ExtendedColors.mint())

        await ctx.respond(embed=embed, ephemeral=True)

    async def play_card(self, ctx: discord.ApplicationContext):
        played_card = await uno.UnoPlayCardView(ctx=ctx, player=self).select_card()

        if played_card:
            processor = UnoTurnProcessor(self.game)
            processor.card_played_event(player=self, card=played_card)
            await self.game.end_current_turn()

    async def draw_card(self, ctx: discord.ApplicationContext):
        warn_msg = "If the card you draw can be played, it will be played automatically. Otherwise, the card will " \
                   "remain in your hand. Either way, you won't be able to take any other actions this turn.\n" \
                   "\n" \
                   "Draw a card?"

        warn_embed = discord.Embed(title="Draw a Card", description=warn_msg, color=support.ExtendedColors.orange())

        conf_data = await support.ConfirmationView(ctx=ctx).request_confirmation(prompt_embeds=[warn_embed],
                                                                                 ephemeral=True)

        conf_success, conf_prompt = conf_data["success"], conf_data["prompt"]

        if not self.game.current_player.value == self:
            msg = "You can only do that when it's your turn. Wait your turn, try again."
            embed = discord.Embed(title="It's not your turn.", description=msg, color=support.ExtendedColors.red())
            await conf_prompt.edit_original_message(embed=embed)

        elif not conf_success:
            msg = "Okay! Make your move whenever you're ready."
            await conf_prompt.edit_original_message(content=msg, embeds=[], view=None)

        else:
            drawn_card_dict = UnoCard.generate_cards(1)[0]
            self.hand.append(drawn_card_dict)

            card = drawn_card_dict["card"]

            processor = UnoTurnProcessor(self.game)

            if self.game.verify_card_playability(card):
                embed = discord.Embed(title="Card Drawn and Played",
                                      description=f"You drew and played a **{card.__str__()}**.",
                                      color=support.ExtendedColors.cyan())

                await conf_prompt.edit_original_message(embeds=[embed], view=None)

                processor.card_drawn_event(player=self)
                processor.card_played_event(player=self, card=card)
            else:
                embed = discord.Embed(title="Card Drawn", description=f"You drew a **{card.__str__()}**.",
                                      color=support.ExtendedColors.dark_blue())

                await conf_prompt.edit_original_message(embeds=[embed], view=None)

                processor.card_drawn_event(player=self)

            await self.game.end_current_turn()

    async def uno_challenge(self):
        pass

    async def wd4_challenge(self):
        pass


class UnoCard:
    """
    Represents an UNO card.
    """

    def __init__(self, color, attribute, emoji: str):
        """
        The constructor for ``UnoCard``. This should **never** be called manually; instead, UnoCard objects should be
        created through the ``generate_cards()`` class method.

        :param color: The color of the card (red, blue, green, yellow).
        :param attribute: The attribute of the card (0-9, Reverse, Skip, Draw Two).
        :param emoji: A string representing the Discord emoji corresponding to the card.
        """
        self.color = color
        self.attribute = attribute
        self.emoji = emoji

    class UnoCardDictionary(TypedDict):
        uuid: str
        card: UnoCard

    @classmethod
    def generate_cards(cls, num_cards) -> list[UnoCardDictionary]:
        """
        Generates UNO cards.

        :param num_cards: The number of cards to generate.
        :return: A list of dictionaries containing key:value pairs of UnoCard objects and unique identifiers for each
        one.
        """
        # this card generation algorithm has an equal chance of generating any one of the 54 distinct UNO cards
        # included in a standard deck. to be more precise, the chance of it generating any given card is 1/54
        # (approx. 1.85%). this differs from a standard UNO game - in a real, physical, UNO deck, not all cards appear
        # with the same frequency.

        # for each color (red, green, blue, yellow), there are 13 cards (ten numbered cards 0-9 + reverse, skip,
        # and draw two)
        colors = ["Red", "Blue", "Green", "Yellow"]
        attrs = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "Reverse", "Skip", "Draw Two"]

        card_emoji = json.load(open(os.path.join(os.getcwd(), "cogs/uno/files/uno_card_emotes.json")))

        # the set of all cards is the cartesian product of the set of colors and the set of all attributes
        all_cards = [cls(color, attribute, card_emoji[color][attribute]) for color in colors for
                     attribute in attrs]

        # wild and wild draw four are special cases, so we create their objects manually and
        # add them to all_cards afterward
        wild = cls("Wild", None, card_emoji["Wild"]["Standard"])
        wd4 = cls("Wild", "Draw Four", card_emoji["Wild"]["Draw Four"])
        all_cards.extend([wild, wd4])

        cards_to_return = []
        for i in range(num_cards):
            # 3515.games uses Discord's select menus
            # (https://discord.com/developers/docs/interactions/message-components#select-menus) to allow users
            # to interactively select a card to play (see cogs.uno.views.UnoPlayCardView). these menus don't allow
            # multiple identical options, but it must be possible for aa user to hold multiple identical cards,
            # so using a dictionary to pair each card with a UUID is an unfortunate workaround to that end.
            cards_to_return.append({"uuid": str(uuid.uuid4()), "card": random.choice(all_cards)})

        return cards_to_return

    def __str__(self):
        if self.attribute:
            return f"{self.color} {self.attribute}"
        else:
            return self.color


class UnoTurnProcessor:
    def __init__(self, game: UnoGame):
        self.game = game

    def card_played_event(self, player: UnoPlayer, card: UnoCard):
        self.game.color_in_play = card.color
        self.game.attribute_in_play = card.attribute

        embed = discord.Embed(title="Card Played", description=f"**{player.user.name}** plays a **{card.__str__()}**.",
                              color=support.ExtendedColors.green())
        embed.set_thumbnail(url=player.user.display_avatar.url)

        self.game.turn_record.append(embed)

    def card_drawn_event(self, player: UnoPlayer):
        embed = discord.Embed(title="Card Drawn", description=f"**{player.user.name}** draws a card.",
                              color=support.ExtendedColors.dark_blue())

        embed.set_thumbnail(url=player.user.display_avatar.url)

        self.game.turn_record.append(embed)
