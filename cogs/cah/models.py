from __future__ import annotations

import asyncio
import copy
import random
import re
from typing import Union

import discord
import inflect as ifl
import nltk
import shortuuid
from llist import dllist as DoublyLinkedList, dllistnode
from sortedcontainers import SortedKeyList

import support
from cogs import cah
from support import HostedMultiplayerGame, posessive

inflect = ifl.engine()


class CAHGame(HostedMultiplayerGame):
    name = "Cards Against Humanity"
    short_name = "CAH"

    def __init__(self, cards: dict, settings: CAHGameSettings, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.min_players = 2

        self.cardset = CAHCardSet(cards)
        self.settings: CAHGameSettings = settings

        self.players = DoublyLinkedList()
        self.is_joinable = True
        self.voice_channel: discord.VoiceChannel = None
        self.banned_users = set()
        self.lobby_intro_msg: discord.Message = None

        self.card_czar = dllistnode()
        self.is_voting = False
        self.turn_uuid = None
        self.black_card: CAHBlackCard = None
        self.candidates: list[CAHCandidateCard] = []

        self.__all_games__[self.thread.id] = self

    async def force_close(self, reason):
        if self.voice_channel:
            await self.voice_channel.delete()

        await super().force_close(reason)

    def retrieve_player(self, user, return_node=False) -> Union[CAHPlayer, dllistnode]:
        """
        Retrieves a player from ``CAHGame().players`` given that player's user object.

        :param user: The user object corresponding to the player. This can be a discord.User, discord.Member, or
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
        Sends an introductory message at the creation of an CAH game thread and pins said message to that thread.
        """
        intro_message = f"{self.host.mention} is the Game Host.\n" \
                        f"\n" \
                        f"To **join**, type `/cah join`. \n" \
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
                        f"The Game Host can begin the game at any time with `/cah host start`. Once the game " \
                        f"has begun, no new players will be able to join."

        intro_embed = discord.Embed(title=f"Welcome to {posessive(self.host.name)} Cards Against Humanity game!",
                                    description=intro_message,
                                    color=support.Color.mint())

        settings_embed = discord.Embed(title="Game Settings", description=str(self.settings),
                                       color=support.Color.mint())

        self.lobby_intro_msg = await self.thread.send(embeds=[intro_embed, settings_embed])
        await self.lobby_intro_msg.pin()

        if self.settings.use_voice:
            await self.create_voice_channel()
            vc_msg = f"Cards Against Humanity is even better with voice chat! Joining the game will grant you access " \
                     f"a private voice channel just for you and the other players. You're not required to use the " \
                     f"channel to play - I think it's more fun if you do, though."
            vc_embed = discord.Embed(title="Join the voice channel!", description=vc_msg,
                                     color=support.Color.magenta())
            await self.thread.send(embed=vc_embed, view=cah.CAHVoiceURLView(self.voice_channel))

    async def create_voice_channel(self) -> discord.VoiceChannel:
        """
        Creates a voice channel for a CAH game.
        """
        guild_categories = self.guild.by_category()
        my_category = discord.utils.find(
            lambda c: c[0] is not None and c[0].name.casefold() == "3515.games", guild_categories
        )
        if my_category:
            my_category = my_category[0]
        else:
            my_category = await self.guild.create_category("3515.games", position=len(guild_categories) + 1)

        overwrites = {
            self.guild.me: discord.PermissionOverwrite.from_pair(
                allow=support.GamePermissions.cah() + support.GamePermissions.cah_voice(),
                deny=discord.Permissions.none()
            ),

            self.guild.default_role: discord.PermissionOverwrite.from_pair(
                allow=discord.Permissions.none(),
                deny=support.GamePermissions.cah() + support.GamePermissions.cah_voice()
            )
        }

        self.voice_channel = await my_category.create_voice_channel(f"{self.short_name} with {self.host.name}!",
                                                                    overwrites=overwrites)

        embed = discord.Embed(title="Nothing to see (or say) here.",
                              description="You should head to the game thread instead.",
                              color=support.Color.red())

        await self.voice_channel.send(embed=embed, view=support.GameThreadURLView(self.thread))

    async def send_vc_deletion_warning(self):
        """
        Sends a warning message to the game thread that the voice channel has been deleted.
        """
        msg = "A moderator has deleted the voice channel for this game. That's fine - " \
              "the game will continue on without it."
        embed = discord.Embed(title="Voice Channel Deleted", description=msg, color=support.Color.red())
        await self.thread.send(content="@everyone", embed=embed)

    async def add_player(self, ctx: discord.ApplicationContext, user: discord.User, is_host=False):
        """
        Adds a player to a not-yet-started CAH game.

        :param ctx: An ApplicationContext object.
        :param user: The discord.User object corresponding to the player.
        :param is_host: Flags whether the player being added is also the Game Host. Defaults to False.
        """
        if user not in await self.thread.fetch_members():
            await self.thread.add_user(user)

        player = CAHPlayer(user=user, game=self)
        self.players.append(player)

        join_message_embed = discord.Embed(title="A new player has joined the game!",
                                           description=f"{user.mention} joined the game. Say hello!",
                                           color=support.Color.mint())

        await self.thread.send(embed=join_message_embed)

        if self.voice_channel:
            await self.voice_channel.set_permissions(
                target=player.user,
                overwrite=player.voice_overwrites()
            )

        if not is_host:
            msg = f"If you didn't mean to join, you can leave the game with `/cah leave`. You can leave at any time, " \
                  f"but if the game has already started, you won't be able to rejoin.\n" \
                  f"\n" \
                  f"Be advised that the Game Host, {self.host.mention}, can kick you at any time, " \
                  f"and if you go AFK mid-game, I'll have you automatically removed for inactivity. Please remember " \
                  f"to be courteous to your fellow players.\n" \
                  f"\n" \
                  f"Have fun!"

            embed = discord.Embed(title=f"Welcome to Cards Against Humanity, {user.name}!", description=msg,
                                  color=support.Color.mint())

            if self.voice_channel:
                vc_msg = f"Cards Against Humanity is best played with voice chat! You can join this game's private " \
                         f"voice channel, {self.voice_channel.mention}, by selecting it in the channel list or " \
                         f"using the button below."
                embed.add_field(name="Join the voice channel!", value=vc_msg, inline=False)

            await ctx.respond(embed=embed,
                              ephemeral=True,
                              view=cah.CAHVoiceURLView(self.voice_channel) if
                              self.voice_channel else None)

    async def remove_player(self, player_node: dllistnode):
        """
        Removes a player from an CAH game.

        :param player_node: The dllistnode object corresponding to the player to be removed.
        """

        player: CAHPlayer = player_node.value

        embed = discord.Embed(title="A player has left the game.",
                              description=f"{player.user.mention} has left the game.",
                              color=support.Color.red())

        await self.thread.send(embed=embed)

        # if the host leaves, the game is force closed
        if player.user == self.host:
            await self.force_close(reason="host_left")

        # if there are too few players remaining in the game and the game has started, the game is force closed
        elif len(self.players) - 1 < self.min_players and not self.is_joinable:
            await self.force_close(reason="insufficient_players")

        elif self.is_voting and player == self.card_czar.value:
            await player.force_vote()

        elif not self.is_voting:
            if player == self.card_czar.value:
                self.card_czar = self.card_czar.next
                msg = f"{self.card_czar.value.user.mention} is now the Card Czar."
                embed = discord.Embed(title="The Card Czar has changed!", description=msg, color=support.Color.orange())
                embed.set_thumbnail(url=self.card_czar.value.user.display_avatar.url)

                await self.thread.send(content=f"{self.card_czar.value.user.mention}, you are now the Card Czar.",
                                       embed=embed)
            else:
                await player.force_pick()

        player_candidate = discord.utils.find(lambda c: c.player == player, self.candidates)
        if player_candidate:
            self.candidates.remove(player_candidate)

        self.players.remove(player_node)

        if self.voice_channel and player.user in self.voice_channel.members:
            await player.user.move_to(None)
            await self.voice_channel.set_permissions(target=player.user, overwrite=None)

    async def inactivity_kick(self, player: CAHPlayer):
        """
        Kicks a player from a CAH game for inactivity.

        :param player: The CAHPlayer object corresponding to the player to be kicked.
        """
        msg = f"{player.user.mention} has been removed for inactivity."
        embed = discord.Embed(title="Player Kicked",
                              description=msg,
                              color=support.Color.red())

        await self.thread.send(embed=embed)
        await self.remove_player(self.retrieve_player(player.user, return_node=True))

        msg = f"You were removed from {self.host.mention}'s Cards Against Humanity game in {self.guild.name} " \
              f"for inactivity."
        embed = discord.Embed(title=f"You timed out of {self.host.name}'s Cards Against Humanity game.",
                              description=msg,
                              color=support.Color.red())

        await player.user.send(embed=embed)

    async def start_game(self):
        """
        Starts a CAH game.
        """
        self.is_joinable = False
        await self.thread.edit(name=f"{self.short_name} with {self.host.name}!")

        random.shuffle(self.players)

        msg = "In Cards Against Humanity, your goal is to earn points by being funny. For some of you, this will " \
              "be a very challenging task.\n" \
              "\n" \
              "Every round, you'll be given a fill-in-the-blank prompt in the form of a " \
              "black card. You'll then use `/cah play` to fill in those blanks with the funniest white cards that " \
              "happen to be at your disposal."

        if self.settings.use_czar:
            msg += " Once everyone has played a white card, the Card Czar will pick whatever submission they " \
                   "think is funniest, and whoever played it gets a point."
        else:
            msg += "Once everyone has played a white card, all players will vote on what they think the funniest " \
                   "submission is. Whichever player played the card that recieved the most votes will get a point."

        msg += f" The first player to reach **{self.settings.points_to_win} points** wins the game.\n" \
               f"\n" \
               f"Let's play!"

        embed = discord.Embed(title="Let's play Cards Against Humanity!", description=msg, color=support.Color.mint())
        embed.set_footer(text="Legal: Writing from Cards Against Humanity is licensed under CC BY-NC-SA 4.0. "
                              "3515.games is not affiliated with or endorsed by Cards Against Humanity, LLC.")

        with support.Assets.cah():
            cah_logo = discord.File("cah_logo.png", filename="cah_logo.png")
            embed.set_image(url="attachment://cah_logo.png")

            await self.thread.send(content="@everyone", embed=embed, file=cah_logo)

        await asyncio.sleep(3)

        for player in self.players.itervalues():
            player.add_cards(10)

        msg = "10 white cards have been dealt to each player. Check them out with `/cah hand`."
        embed = discord.Embed(title="The game begins!", description=msg, color=support.Color.mint())
        await self.thread.send(embed=embed)

        await asyncio.sleep(2)

        await self.start_new_round()

    async def start_new_round(self):
        """
        Starts a new round of a CAH game.
        """
        self.turn_uuid = shortuuid.uuid()
        self.card_czar = self.card_czar.next if self.card_czar and self.card_czar.next else self.players.first
        self.black_card = self.cardset.get_random_black()
        self.candidates.clear()

        for player in self.players.itervalues():
            player.has_submitted = False

        card_embed = discord.Embed(title="Black Card",
                                   description=self.black_card.text,
                                   color=support.Color.black())
        card_embed.set_footer(
            text=f"{self.card_czar.value.user.name} is the Card Czar.",
            icon_url=self.card_czar.value.user.display_avatar.url
        )

        await self.thread.send(content=f"@everyone Pick {inflect.number_to_words(self.black_card.pick)} "
                                       f"white {inflect.plural('card', self.black_card.pick)} with "
                                       f"`/cah play`. {self.card_czar.value.user.mention} is the "
                                       f"Card Czar.", embed=card_embed)

        await self.turn_timer()

    async def start_voting(self):
        """
        Starts the voting phase of a CAH round.
        """
        self.turn_uuid = shortuuid.uuid()
        self.is_voting = True

        msg = f"**{self.card_czar.value.user.name}** is the Card Czar."
        embed = discord.Embed(title="It's voting time!", description=msg, color=support.Color.mint())
        embed.set_thumbnail(url=self.card_czar.value.user.display_avatar.url)

        for i, candidate in enumerate(self.candidates):
            embed.add_field(name=f"Submission {i + 1}", value=candidate.text, inline=True)
            if i + 1 % 3 == 0:
                embed.add_field(name="\u200b", value="\u200b", inline=False)

        await self.thread.send(content=f"{self.card_czar.value.user.mention} Select your favorite submission "
                                       f"with `/cah vote`.", embed=embed)

        await self.turn_timer()

    async def submit_vote(self, candidate: CAHCandidateCard):
        """
        Submits a vote for a candidate card.

        :param candidate: The candidate card to submit a vote for.
        """
        await self.end_round(winning_submission=candidate)

    async def end_round(self, winning_submission: CAHCandidateCard):
        """
        Ends a round of a CAH game.

        :param winning_submission: The round's winning submission.
        """
        self.turn_uuid = None
        self.is_voting = False

        victor = winning_submission.player
        victor.points += 1

        if self.settings.use_czar:
            msg = "The Card Czar has "
        else:
            msg = "The players have "

        msg += f"chosen {victor.user.mention}'s submission.\n" \
               f"\n" \
               f"**{victor.user.name}** now has **{victor.points} " \
               f"{inflect.plural('point', victor.points)}**, putting them in " \
               f"{victor.get_ranking()} place"

        if victor.points < self.settings.points_to_win:
            point_gap = self.settings.points_to_win - victor.points
            msg += f" – {point_gap} {inflect.plural('point', point_gap)} away from winnning the game."
        else:
            msg += " and winning them the game."

        embed = discord.Embed(title=f"{victor.user.name} gains a point!",
                              description=msg,
                              color=support.Color.mint())
        embed.add_field(name="Winning Submission", value=winning_submission.text, inline=False)
        embed.set_thumbnail(url=victor.user.display_avatar.url)

        await self.thread.send(embed=embed)

        if winning_submission.player.points >= self.settings.points_to_win:
            await self.end_game(victor)
        else:
            await asyncio.sleep(5)
            await self.start_new_round()

    async def end_game(self, game_winner: CAHPlayer):
        """
        Ends a CAH game. Triggered only by the win condition; other endings are handled by ``force_close()``.

        :param game_winner: The winner of the game.
        """
        self.__all_games__.pop(self.thread.id)

        msg = f"Congratulations, {game_winner.user.mention}! You won Cards Against Humanity!\n" \
              f"\n" \
              f"This thread will be automatically deleted in 60 seconds. Thanks for playing!"

        embed = discord.Embed(title=f"Game Over! {game_winner.user.name} Wins!", description=msg,
                              color=support.Color.mint())
        embed.set_thumbnail(url=game_winner.user.display_avatar.url)
        await self.thread.edit(name=f"CAH with {self.host.name} - Game Over!")
        msg = await self.thread.send(content="@everyone", embed=embed)
        await msg.pin()

        await asyncio.sleep(60)
        await self.thread.delete()

    async def turn_timer(self):
        """
        Enforces a time limit on player actions.
        """

        async def play_callback():
            """
            The time limit trigger for playing cards.
            """
            outstanding_players = [player for player in self.players.itervalues() if not player.has_submitted
                                   and player != self.card_czar.value]
            mentions = [player.user.mention for player in outstanding_players]
            msg = "The mentioned players have timed out. I've made their submissions for them."
            embed = discord.Embed(title="Time's up.", description=msg, color=support.Color.red())
            await self.thread.send(content="".join(mentions), embed=embed)

            for player in outstanding_players:
                await player.increment_timeouts()
                await player.force_pick()

        async def vote_callback():
            """
            The time limit trigger for voting.
            """
            msg = "You timed out. I've cast your vote for you."
            embed = discord.Embed(title="Time's up.", description=msg, color=support.Color.red())
            await self.thread.send(content=self.card_czar.value.user.mention, embed=embed)

            await self.card_czar.value.increment_timeouts()

            await self.card_czar.value.force_vote()

        turn_uuid = self.turn_uuid

        await asyncio.sleep(self.settings.timeout)

        if turn_uuid == self.turn_uuid and self.retrieve_game(self.thread.id):
            await play_callback() if not self.is_voting else await vote_callback()

    def get_leaderboard(self) -> list[[list[CAHPlayer]]]:
        """
        Returns the game leaderboard.
        """
        point_order = reversed(SortedKeyList(self.players.itervalues(), key=lambda p: p.points))

        leaderboard = []
        determinant = 0
        for player in point_order:
            if not leaderboard or player.points < determinant:
                leaderboard.append([player])
                determinant = player.points
            else:
                leaderboard[-1].append(player)

        return leaderboard

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

        embed = discord.Embed(title=f"You were kicked from {posessive(self.host.name)} CAH game.",
                              description=f"You were kicked from {self.host.name}'s CAH game in {self.guild.name}.",
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


class CAHPopularVoteGame(CAHGame):
    """
    A subclass of ``CAHGame`` adapted for popular vote gameplay.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def remove_player(self, player_node: dllistnode):
        player: CAHPlayer = player_node.value

        embed = discord.Embed(title="A player has left the game.",
                              description=f"{player.user.mention} has left the game.",
                              color=support.Color.red())

        await self.thread.send(embed=embed)

        # if the host leaves, the game is force closed
        if player.user == self.host:
            await self.force_close(reason="host_left")

        # if there are too few players remaining in the game and the game has started, the game is force closed
        elif len(self.players) - 1 < self.min_players and not self.is_joinable:
            pass
            await self.force_close(reason="insufficient_players")

        elif self.is_voting:
            await player.force_vote()

        else:
            await player.force_pick()

        player_candidate = discord.utils.find(lambda c: c.player == player, self.candidates)
        if player_candidate:
            self.candidates.remove(player_candidate)

        self.players.remove(player_node)

        if self.voice_channel and player.user in self.voice_channel.members:
            await player.user.move_to(None)
            await self.voice_channel.set_permissions(target=player.user, overwrite=None)

    async def start_new_round(self):
        self.turn_uuid = shortuuid.uuid()
        self.black_card = self.cardset.get_random_black()
        self.candidates.clear()

        for player in self.players.itervalues():
            player.has_submitted = False
            player.has_voted = False

        card_embed = discord.Embed(title="Black Card",
                                   description=self.black_card.text,
                                   color=support.Color.black())

        await self.thread.send(content=f"@everyone Pick {inflect.number_to_words(self.black_card.pick)} "
                                       f"white {inflect.plural('card', self.black_card.pick)} with "
                                       f"`/cah play`.", embed=card_embed)

        await self.turn_timer()

    async def start_voting(self):
        self.turn_uuid = shortuuid.uuid()
        self.is_voting = True

        msg = f"Vote for your favorite submission with `/cah vote`."
        embed = discord.Embed(title="It's voting time!", description=msg, color=support.Color.mint())

        for i, candidate in enumerate(self.candidates):
            embed.add_field(name=f"Submission {i + 1}", value=candidate.text, inline=True)
            if i + 1 % 3 == 0:
                embed.add_field(name="\u200b", value="\u200b", inline=False)

        await self.thread.send(content="@everyone", embed=embed)

        await self.turn_timer()

    async def submit_vote(self, candidate: CAHCandidateCard):
        real_candidate = discord.utils.find(lambda c: c.uuid == candidate.uuid, self.candidates)
        real_candidate.votes += 1

        if all(player.has_voted for player in self.players.itervalues()):
            # determine the highest vote total
            max_points = max(candidate.votes for candidate in self.candidates)

            # get a list of candidates with the highest vote total
            potential_winners = [candidate for candidate in self.candidates if candidate.votes == max_points]

            # pick a winner at random from the aforementioned list. this is redundant if there is only one potential
            # winner, but fairly resolves ties in the event there are multiple potential winners.
            await self.end_round(random.choice(potential_winners))

    async def turn_timer(self):
        async def play_callback():
            outstanding_players = [player for player in self.players.itervalues() if not player.has_submitted]
            mentions = [player.user.mention for player in outstanding_players]
            msg = "The mentioned players have timed out. I've made their submissions for them."
            embed = discord.Embed(title="Time's up.", description=msg, color=support.Color.red())
            await self.thread.send(content="".join(mentions), embed=embed)

            for player in outstanding_players:
                await player.increment_timeouts()
                await player.force_pick()

        async def vote_callback():
            outstanding_players = [player for player in self.players.itervalues() if not player.has_submitted]
            mentions = [player.user.mention for player in outstanding_players]

            msg = "The mentioned players have timed out. I've cast their votes for them."
            embed = discord.Embed(title="Time's up.", description=msg, color=support.Color.red())
            await self.thread.send(content="".join(mentions), embed=embed)

            for player in outstanding_players:
                await player.increment_timeouts()
                await player.force_vote()

        turn_uuid = self.turn_uuid

        await asyncio.sleep(self.settings.timeout)

        if turn_uuid == self.turn_uuid and self.retrieve_game(self.thread.id):
            await play_callback() if not self.is_voting else await vote_callback()


class CAHGameSettings:
    def __init__(self, max_players: int, points_to_win: int, timeout: int, use_czar: bool, use_voice: bool):
        self.max_players = max_players
        self.points_to_win = points_to_win
        self.timeout = timeout
        self.use_czar = use_czar
        self.use_voice = use_voice

    def __str__(self):
        players_str = f"__**Maximum Players**: {self.max_players}__\n" \
                      f"Up to {self.max_players} can join this CAH game. Once that quota is filled, " \
                      f"no one else will be able to join unless a player leaves or is removed by the Game Host."

        points_str = f"__**Points to Win**: {self.points_to_win}__\n" \
                     f"The first player to reach {self.points_to_win} points will win the game."

        timeout_str = f"__**Timeout**: {self.timeout} seconds__\n" \
                      f"Each player will have {self.timeout} seconds to play white cards when prompted. " \
                      f"When it's voting time, {'the Card Czar' if self.use_czar else 'players'} will have " \
                      f"{self.timeout} seconds to vote for a white card."

        voting_str = f"__**Voting Mode**: {'Card Czar' if self.use_czar else 'Popular Vote'}__\n" \
                     f"At the end of each round, the funniest submission will be decided by " \
                     f"{'a Card Czar' if self.use_czar else 'popular vote'}."

        return "\n\n".join([players_str, points_str, timeout_str, voting_str])


class CAHPlayer:
    def __init__(self, user: discord.Member, game: CAHGame):
        self.user = user
        self.game = game

        self.points = 0
        self.consecutive_timeouts = 0
        self.hand: list[str] = []
        self.has_submitted: bool = False
        self.has_voted: bool = False  # only used in popular vote games

        self.terminable_views: list[support.EnhancedView] = []

    async def show_hand(self, ctx: discord.ApplicationContext):
        """
        Shows the player the white cards they're currently holding.
        """
        embed = discord.Embed(title="Your White Cards",
                              description=f"Here are the white cards you're currently holding:\n\n"
                                          f"{chr(10).join([f'- {card}' for card in self.hand])}",
                              color=support.Color.white())

        await ctx.respond(embed=embed, ephemeral=True)

    async def pick_cards(self, ctx: discord.ApplicationContext):
        """
        Prompts the player to pick white cards to play.
        """
        candidate: CAHCandidateCard = await cah.CAHCardSelectView(ctx=ctx, player=self).select_card()

        if candidate:
            self.reset_timeouts()
            await self.submit_candidate(candidate)

    async def force_pick(self, player_removal: bool = False):
        """
        Picks white cards on the player's behalf.
        :param player_removal: Flags whether the cards are being picked on the player's behalf as a result of them
        being removed from the game.
        """
        # pick x number of cards from the player's hand at random, depending on how many white cards need to be played
        cards = [self.hand[i] for i in random.sample(range(len(self.hand)), self.game.black_card.pick)]
        # create candidates from those cards and randomly choose one of them to submit
        candidate: CAHCandidateCard = random.choice(CAHCandidateCard.make_candidates(self, *cards))

        await self.submit_candidate(candidate, player_removal=player_removal)

    async def submit_candidate(self, candidate: CAHCandidateCard, player_removal: bool = False):
        """
        Submits the player's candidate card.
        :param candidate: The candidate card to submit.
        :param player_removal: Flags whether the submission is being made on the player's behalf as a result of them
        being removed from the game.
        """
        self.has_submitted = True

        if not player_removal:
            self.game.candidates.append(candidate)

        await self.terminate_views()

        for card in candidate.white_cards:
            self.hand.remove(card)

        self.add_cards(10 - len(self.hand))

        if all(player.has_submitted for player in self.game.players.itervalues()
               if player != self.game.card_czar.value):
            await self.game.start_voting()

    async def vote(self, ctx: discord.ApplicationContext):
        """
        Prompts the player to vote for a candidate card.
        """
        selection: CAHCandidateCard = await cah.CAHVotingView(ctx=ctx, game=self.game).vote()

        if selection:
            self.has_voted = True
            self.reset_timeouts()
            await self.terminate_views()
            await self.game.submit_vote(candidate=selection)

    async def force_vote(self):
        """
        Votes for a candidate card on the player's behalf.
        """
        await self.terminate_views()
        await self.game.submit_vote(candidate=random.choice(self.game.candidates))

    def add_cards(self, num_cards):
        """
        Adds white cards to the player's hand.

        :param num_cards: The number of white cards to add to the player's hand.
        """
        self.hand.extend(self.game.cardset.get_random_white(num_cards))

    def voice_overwrites(self) -> discord.Permissions:
        """
        Returns the voice channel permission overwrites for the player.
        """
        if self.game.host == self.user:
            overwrites = {
                "allow": discord.Permissions.voice() - discord.Permissions.stream,
                "deny": discord.Permissions.none()
            }
        else:
            overwrites = {
                "allow": discord.Permissions(connect=True, speak=True, use_voice_activation=True),
                "deny": discord.Permissions.none()
            }

        overwrites["allow"] += discord.Permissions(view_channel=True, read_message_history=True)

        return discord.PermissionOverwrite.from_pair(**overwrites)

    def get_ranking(self, with_string: bool = False) -> str:
        """
        Returns a string representation of the player's ranking in the game. (e.g. "1st", "2nd", "3rd", etc.).

        :param with_string: If True, the method will return the full ranking string in the
        format "Xth of Y (tied with Z others)".
        """
        leaderboard_group = discord.utils.find(lambda group: self in group, self.game.get_leaderboard())
        ranking = inflect.ordinal(self.game.get_leaderboard().index(leaderboard_group) + 1)

        if with_string:
            ranking += f" of {len(self.game.players)}"
            ties = len(leaderboard_group) - 1

            if ties > 0:
                ranking += f" (tied with {ties} {inflect.plural('other', ties)})"

        return ranking

    async def increment_timeouts(self):
        """
        Increments the player's timeout counter by one.
        """
        self.consecutive_timeouts += 1

        if self.consecutive_timeouts >= 3:
            await self.game.inactivity_kick(self)

    def reset_timeouts(self):
        """
        Resets the player's timeout counter to 0.
        """
        self.consecutive_timeouts = 0

    async def terminate_views(self):
        """
        Terminates time-sensitive views.
        """
        for view in self.terminable_views:
            if not view.is_finished():
                await view.full_stop()

    def __str__(self):
        return self.user.name


class CAHBlackCard:
    """
    Represents a black card in a Cards Against Humanity game.
    """

    def __init__(self, text: str, pick: int):
        if "_" not in text:
            text += " _"

        self.text = discord.utils.escape_markdown(text.replace("_", "_" * 5))
        self.pick = pick

    def __str__(self):
        return self.text


class CAHCandidateCard:
    """
    Represents a candidate card in a Cards Against Humanity game. A candidate card is a black card whose blank spaces
    have been filled by white cards.
    """

    def __init__(self, text: str, player: CAHPlayer, *white_cards: str):
        self.text = text
        self.player = player
        self.white_cards = white_cards

        self.votes = 0  # only used in popular vote games
        self.uuid = shortuuid.uuid()

    @classmethod
    def make_candidates(cls, player: CAHPlayer, *white_cards) -> list[CAHCandidateCard]:
        """
        Creates candidate cards.

        :param player: The :class:`CAHPlayer` who the candidate cards will belong to.
        :param white_cards: The white cards to create candidate cards from.
        :return: A list of candidate cards.
        """
        # this algorithm is designed to insert white cards into black cards in a way that attempts to maintain
        # grammatical correctness and proper noun capitalization. the enormity of the dataset it has to work with
        # and the innumerable amount of possible edge cases mean it will sometimes produce less-than-perfect results.

        candidates = []

        underscores = discord.utils.escape_markdown("_" * 5)
        punctuation = ".?!:"

        proper_nouns = []
        for card in white_cards:
            words = re.sub(r"[.?!,]", "", card).split()
            proper_nouns.extend([word for word, pos in nltk.pos_tag(words) if pos.startswith("NNP")])

        for c1, c2 in zip(white_cards, reversed(white_cards)):
            tokens = DoublyLinkedList(re.split(r"((?:\\_){5})", player.game.black_card.text))
            if not tokens[-1]:
                tokens.pop()

            for card in c1, c2:
                if underscores in tokens:
                    underscore_node: dllistnode = tokens.nodeat([*tokens].index(underscores))

                    strip: bool = underscore_node.prev is None or underscore_node.next is not None

                    decapitalize: bool = (underscore_node.prev is not None
                                          and not underscore_node.prev.value.rstrip().endswith(tuple(punctuation))
                                          and card.split()[0] not in proper_nouns)

                    if strip:
                        card = card.rstrip(punctuation)

                    if decapitalize:
                        card = card[0].lower() + card[1:]

                    tokens.insertbefore(f"**{card}**", underscore_node)
                    tokens.remove(underscore_node)

            if len(candidates) < player.game.black_card.pick:
                candidates.append(cls("".join(tokens), player, *white_cards))
            else:
                break

        return candidates

    def __str__(self):
        return self.text


class CAHCardSet:
    """
    Represents a set of black and white cards in a Cards Against Humanity game.
    """

    def __init__(self, cards: dict):
        # the cards parameter should be a dictionary derived from a JSON object obtained from an API call to
        # REST Against Humanity. https://restagainsthumanity.com

        def sanitize_white(card):
            """
            Ensures white cards begin with a capital letter and end with a punctuation mark.

            :param card: The white card to sanitize.
            """
            return card[0].upper() + re.sub(r"\b$", ".", card[1:])

        # due to Discord limitations, white cards must be 60 characters or fewer
        self.black: list[CAHBlackCard] = [CAHBlackCard(**card) for card in cards["black"]]
        self.white: list[str] = [sanitize_white(card) for card in cards["white"] if len(sanitize_white(card)) <= 60]
        self.backup: CAHCardSet = copy.deepcopy(self)

    def get_random_black(self) -> CAHBlackCard:
        """
        Returns a random black card. Returned black cards are removed from the set.
        """
        if not self.black:
            self.reset()

        return self.black.pop(random.randint(0, len(self.black) - 1))

    def get_random_white(self, num_cards=1) -> list[str]:
        """
        Returns a list containing a given number of random white cards. Returned white cards are removed from the set.
        Lists returned by this method will never contain duplicate white cards.

        :param num_cards: The number of white cards to return. Defaults to 1. If greater than the total number of white
        cards in the set, all white cards will be returned.
        """
        if num_cards > len(self.white):
            self.reset()
            num_cards = min(num_cards, len(self.white))

        cards = [self.white[i] for i in random.sample(range(len(self.white)), num_cards)]
        self.white = list(set(self.white) - set(cards))

        return cards

    def reset(self):
        """
        Restores the cardset to its original state.
        """
        self.backup.backup = copy.deepcopy(self.backup)
        self.__dict__ = self.backup.__dict__
