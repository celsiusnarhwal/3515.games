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
from attrs import define
from elysia import Fields
from llist import dllist, dllistnode
from sortedcontainers import SortedKeyList

import shrine
import support
from cogs import cah
from keyboard import *
from shrine.kami import posessive
from support import HostedGame

inflect = ifl.engine()


@define(slots=False)
class CAHGame(HostedGame):
    """
    A Cards Against Humanity game.
    """

    __games__: ClassVar = {}

    name: ClassVar = "Cards Against Humanity"
    short_name: ClassVar = "CAH"
    min_players: ClassVar = 2

    deck: cah.CAHDeck
    settings: CAHGameSettings

    players: dllist = Fields.attr(factory=dllist)
    banned_users: set[discord.User] = Fields.attr(factory=set)
    card_czar: dllistnode = Fields.attr(factory=dllistnode)
    is_voting: bool = Fields.attr(default=False)
    turn_uuid: uuid.UUID = Fields.attr(default=None)
    black_card: cah.CAHBlackCard = Fields.attr(default=None)
    candidates: list[cah.CAHCandidateCard] = Fields.attr(factory=list)

    def __attrs_post_init__(self):
        super().__attrs_post_init__()

        if not self.settings.use_czar:
            self.__class__ = CAHPopularVoteGame

    async def force_close(self, reason):
        if self.voice_channel:
            await self.voice_channel.delete()

        await super().force_close(reason)

    def retrieve_player(
        self, user: discord.User, return_node: bool = False
    ) -> cah.CAHPlayer | dllistnode:
        """
        Convert a :class:`discord.User` object to its corresponding :class:`CAHPlayer` object, if one exists.

        Parameters
        ----------
        user: discord.User
            The player's user object.
        return_node: bool
            Whether to return the node containing the player object or the player object itself.

        Returns
        -------
        cah.CAHPlayer | dllistnode
            The player object or the node containing the player object.
        """

        if return_node:
            return discord.utils.find(
                lambda node: node.value.user.id == user.id, self.players.iternodes()
            )
        else:
            return discord.utils.find(
                lambda player: player.user.id == user.id, self.players.itervalues()
            )

    async def open_lobby(self):
        with shrine.Torii.cah() as torii:
            template = torii.get_template("lobby-open.md")
            intro_message = template.render(host=self.host.mention)

        intro_embed = discord.Embed(
            title=f"Welcome to {posessive(self.host.name)} Cards Against Humanity game!",
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

    async def add_player(
        self, ctx: discord.ApplicationContext, user: discord.User, is_host=False
    ):
        """
        Add a player to the game.

        Parameters
        ----------
        ctx: discord.ApplicationContext

        user: discord.User
            The player to add.
        is_host: bool
            Whether the player is the Game Host.
        """
        if user not in await self.thread.fetch_members():
            await self.thread.add_user(user)

        player = cah.CAHPlayer(user=user, game=self)
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
                f"If you didn't mean to join, you can leave the game with `/cah leave`. You can leave at any time, "
                f"but if the game has already started, you won't be able to rejoin.\n"
                f"\n"
                f"Be advised that the Game Host, {self.host.mention}, can kick you at any time, "
                f"and if you go AFK mid-game, I'll have you automatically removed for inactivity. Please remember "
                f"to be courteous to your fellow players.\n"
                f"\n"
                f"Have fun!"
            )

            embed = discord.Embed(
                title=f"Welcome to Cards Against Humanity, {user.name}!",
                description=msg,
                color=support.Color.mint(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

    async def remove_player(self, player_node: dllistnode):
        """
        Remove a player from the game.

        Parameters
        ----------
        player_node: dllistnode
            The node containing the player to remove.
        """

        player: cah.CAHPlayer = player_node.value

        embed = discord.Embed(
            title="A player has left the game.",
            description=f"{player.user.mention} has left the game.",
            color=support.Color.error(),
        )

        await self.thread.send(embed=embed)

        # if the host leaves, the game is force closed
        if player.user == self.host:
            await self.force_close(reason="host_left")

        elif self.has_started:
            # if there are too few players remaining in the game and the game has started, the game is force closed
            if len(self.players) - 1 < self.min_players:
                await self.force_close(reason="insufficient_players")

            elif self.is_voting and player == self.card_czar.value:
                await player.force_vote()

            elif not self.is_voting:
                if player == self.card_czar.value:
                    self.card_czar = self.card_czar.next
                    msg = f"{self.card_czar.value.user.mention} is now the Card Czar."
                    embed = discord.Embed(
                        title="The Card Czar has changed!",
                        description=msg,
                        color=support.Color.caution(),
                    )
                    embed.set_thumbnail(
                        url=self.card_czar.value.user.display_avatar.url
                    )

                    await self.thread.send(
                        content=f"{self.card_czar.value.user.mention}, you are now the Card Czar.",
                        embed=embed,
                    )
                else:
                    await player.force_pick()

            player_candidate = discord.utils.find(
                lambda c: c.player == player, self.candidates
            )
            if player_candidate:
                self.candidates.remove(player_candidate)

        self.players.remove(player_node)

        if self.voice_channel and player.user in self.voice_channel.members:
            await player.user.move_to(None)
            await self.voice_channel.set_permissions(target=player.user, overwrite=None)

    async def inactivity_kick(self, player: cah.CAHPlayer):
        """
        Kick a player for inactivity.

        Parameters
        ----------
        player: cah.CAHPlayer
            The player to kick.
        """
        msg = f"{player.user.mention} has been removed for inactivity."
        embed = discord.Embed(
            title="Player Kicked", description=msg, color=support.Color.error()
        )

        await self.thread.send(embed=embed)
        await self.remove_player(self.retrieve_player(player.user, return_node=True))

        msg = (
            f"You were removed from {self.host.mention}'s Cards Against Humanity game in {self.guild.name} "
            f"for inactivity."
        )
        embed = discord.Embed(
            title=f"You timed out of {self.host.name}'s Cards Against Humanity game.",
            description=msg,
            color=support.Color.error(),
        )

        await player.user.send(embed=embed)

    async def start_game(self):
        """
        Start the game.
        """
        self.is_joinable = False
        await self.thread.edit(name=f"{self.short_name} with {self.host.name}!")

        random.shuffle(self.players)

        with shrine.Torii.cah() as torii:
            template = torii.get_template("game-start.md")
            msg = template.slender(settings=self.settings)

        embed = discord.Embed(
            title="Let's play Cards Against Humanity!",
            description=msg,
            color=support.Color.mint(),
        )
        embed.set_footer(
            text="Legal: Writing from Cards Against Humanity is licensed under CC BY-NC-SA 4.0. "
            "3515.games is not affiliated with or endorsed by Cards Against Humanity, LLC."
        )

        with support.Assets.cah():
            cah_logo = discord.File("cah_logo.png", filename="cah_logo.png")
            embed.set_image(url="attachment://cah_logo.png")

            await self.thread.send(content="@everyone", embed=embed, file=cah_logo)

        await asyncio.sleep(3)

        for player in self.players.itervalues():
            player.add_cards(10)

        msg = "10 white cards have been dealt to each player. Check them out with `/cah hand`."
        embed = discord.Embed(
            title="The game begins!", description=msg, color=support.Color.mint()
        )
        await self.thread.send(embed=embed)

        await asyncio.sleep(2)

        await self.start_round()

    async def start_round(self):
        """
        Start a new round.
        """
        self.turn_uuid = uuid.uuid4()
        self.card_czar = (
            self.card_czar.next
            if self.card_czar and self.card_czar.next
            else self.players.first
        )
        self.black_card = self.deck.get_random_black()
        self.candidates.clear()

        for player in self.players.itervalues():
            player.has_submitted = False

        card_embed = discord.Embed(
            title="Black Card",
            description=self.black_card.text,
            color=support.Color.black(),
        )
        card_embed.set_footer(
            text=f"{self.card_czar.value.user.name} is the Card Czar.",
            icon_url=self.card_czar.value.user.display_avatar.url,
        )

        await self.thread.send(
            content=f"@everyone Pick {inflect.number_to_words(self.black_card.pick)} "
            f"white {inflect.plural('card', self.black_card.pick)} with "
            f"`/cah play`. {self.card_czar.value.user.mention} is the "
            f"Card Czar.",
            embed=card_embed,
        )

        await self.turn_timer()

    async def start_voting(self):
        """
        Start the voting phase of the current round.
        """
        self.turn_uuid = uuid.uuid4()
        self.is_voting = True

        msg = f"**{self.card_czar.value.user.name}** is the Card Czar."
        embed = discord.Embed(
            title="It's voting time!", description=msg, color=support.Color.mint()
        )
        embed.set_thumbnail(url=self.card_czar.value.user.display_avatar.url)

        for i, candidate in enumerate(self.candidates):
            embed.add_field(
                name=f"Submission {i + 1}", value=candidate.text, inline=True
            )
            if (i + 1) % 3 == 0:
                embed.add_field(name="\u200b", value="\u200b", inline=False)

        await self.thread.send(
            content=f"{self.card_czar.value.user.mention} Select your favorite submission "
            f"with `/cah play`.",
            embed=embed,
        )

        await self.turn_timer()

    async def submit_vote(self, candidate: cah.CAHCandidateCard, **_):
        """
        Submit a vote for a candidate card.

        Parameters
        ----------
        candidate: cah.CAHCandidateCard
            The candidate card.
        """
        await self.end_round(winning_submission=candidate)

    async def end_round(self, winning_submission: cah.CAHCandidateCard):
        """
        End the current round.

        Parameters
        ----------
        winning_submission: cah.CAHCandidateCard
            The winning submission.
        """
        self.turn_uuid = None
        self.is_voting = False

        victor = winning_submission.player
        victor.points += 1

        victor_rank = inflect.ordinal(
            self.get_leaderboard().index(
                discord.utils.find(
                    lambda group: victor in group, self.get_leaderboard()
                )
            )
            + 1
        )

        msg = (
            f"The {'Card Czar has ' if self.settings.use_czar else 'players have '} "
            f"chosen {posessive(victor.mention)} submission.\n"
            f"\n"
            f"**{victor.name}** now has {inflect.no('Awesome Point', victor.points)}, "
            f"putting them in {victor_rank} place."
        )

        if (point_gap := self.settings.points_to_win - victor.points) > 0:
            msg = (
                msg[:-1]
                + f"—**{inflect.no('Awesome Point', point_gap)}** away from winning the game."
            )

        embed = discord.Embed(
            title=f"{victor.user.name} gains a Awesome Point!",
            description=msg,
            color=support.Color.mint(),
        )
        embed.add_field(
            name="Winning Submission", value=winning_submission.text, inline=False
        )
        embed.set_thumbnail(url=victor.user.display_avatar.url)

        await self.thread.send(embed=embed)

        if winning_submission.player.points >= self.settings.points_to_win:
            await self.end_game(victor)
        else:
            await asyncio.sleep(5)
            await self.start_round()

    async def end_game(self, game_winner: cah.CAHPlayer):
        """
        End the game.

        Parameters
        ----------
        game_winner: cah.CAHPlayer
            The player who won the game.

        Notes
        -----
        This method is only triggered when a player meets the win condition; other game-ending scenarios are
        handled by :meth:`force_close`.
        """
        self.__games__.pop(self.thread.id)

        msg = (
            f"Congratulations, {game_winner.user.mention}! You won Cards Against Humanity!\n"
            f"\n"
            f"This thread will be automatically deleted in 60 seconds. Thanks for playing!"
        )

        embed = discord.Embed(
            title=f"Game Over! {game_winner.user.name} Wins!",
            description=msg,
            color=support.Color.mint(),
        )
        embed.set_thumbnail(url=game_winner.user.display_avatar.url)
        await self.thread.edit(name=f"CAH with {self.host.name} - Game Over!")
        msg = await self.thread.send(content="@everyone", embed=embed)
        await msg.pin()

        await asyncio.sleep(60)
        await self.thread.delete()

    async def turn_timer(self):
        """
        Start a timer for the current turn.

        The game will forcefully progress if this timer expires and the current turn has not yet ended.
        """

        async def play_callback():
            """
            The time limit trigger for playing cards.
            """
            outstanding_players = [
                player
                for player in self.players.itervalues()
                if not player.has_submitted and player != self.card_czar.value
            ]
            mentions = [player.user.mention for player in outstanding_players]
            msg = "The mentioned players have timed out. I've made their submissions for them."
            embed = discord.Embed(
                title="Time's up.", description=msg, color=support.Color.error()
            )
            await self.thread.send(content="".join(mentions), embed=embed)

            for player in outstanding_players:
                await player.increment_timeouts()

                if self.retrieve_player(player.user):
                    await player.force_pick()

        async def vote_callback():
            """
            The time limit trigger for voting.
            """
            msg = "You timed out. I've cast your vote for you."
            embed = discord.Embed(
                title="Time's up.", description=msg, color=support.Color.error()
            )
            await self.thread.send(
                content=self.card_czar.value.user.mention, embed=embed
            )

            await self.card_czar.value.increment_timeouts()

            if self.retrieve_player(self.card_czar.value.user):
                await self.card_czar.value.force_vote()

        turn_uuid = self.turn_uuid

        await asyncio.sleep(support.fuzz(self.settings.timeout))

        if turn_uuid == self.turn_uuid and self.retrieve_game(self.thread.id):
            await play_callback() if not self.is_voting else await vote_callback()

    def get_leaderboard(self) -> list[[list[cah.CAHPlayer]]]:
        """
        Returns the game leaderboard.
        """
        point_order = reversed(
            SortedKeyList(self.players.itervalues(), key=lambda p: p.points)
        )

        leaderboard = []
        determinant = 0
        for player in point_order:
            if not leaderboard or player.points < determinant:
                leaderboard.append([player])
                determinant = player.points
            else:
                leaderboard[-1].append(player)

        return leaderboard

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
        Kick a player from the game.

        Parameters
        ----------
        player_node: dllistnode
            The node of the player to kick.

        Notes
        -----
        This method is only invoked at the explicit request of the Game Host. It shouldn't be confused with
        :meth:`inactivity_kick`, which is invoked automatically to punish idle players.
        """
        embed = discord.Embed(
            title="Player Kicked",
            description=f"{player_node.value.user.mention} has been kicked from the game.",
            color=support.Color.error(),
        )

        await self.thread.send(embed=embed)
        await self.remove_player(player_node)

        embed = discord.Embed(
            title=f"You were kicked from {posessive(self.host.name)} CAH game.",
            description=f"You were kicked from {self.host.name}'s CAH game in {self.guild.name}.",
            color=support.Color.error(),
        )

        embed.timestamp = discord.utils.utcnow()

        await player_node.value.user.send(embed=embed)


class CAHPopularVoteGame(CAHGame):
    """
    A Cards Against Humanity game where winners are determined by popular vote rather than a Card Czar.

    An object of this class is created rather than a :class:`CAHGame` object when `/cah create` command is invoked
    with the `voting` option set to "Popular Vote".

    This class overrides the functionality of some methods to accommodate the popular vote system. Its objects
    can generally be treated as equivalent to those of :class:`CAHGame`.
    """

    async def remove_player(self, player_node: dllistnode):
        player: cah.CAHPlayer = player_node.value

        embed = discord.Embed(
            title="A player has left the game.",
            description=f"{player.user.mention} has left the game.",
            color=support.Color.error(),
        )

        await self.thread.send(embed=embed)

        # if the host leaves, the game is force closed
        if player.user == self.host:
            await self.force_close(reason="host_left")

        # if there are too few players remaining in the game and the game has started, the game is force closed
        elif len(self.players) - 1 < self.min_players and not self.is_joinable:
            await self.force_close(reason="insufficient_players")

        elif not self.is_joinable:
            await player.force_vote() if self.is_voting else await player.force_pick()

            player_candidate = discord.utils.find(
                lambda c: c.player == player, self.candidates
            )
            if player_candidate:
                self.candidates.remove(player_candidate)

        self.players.remove(player_node)

        if self.voice_channel and player.user in self.voice_channel.members:
            await player.user.move_to(None)
            await self.voice_channel.set_permissions(target=player.user, overwrite=None)

    async def start_round(self):
        self.turn_uuid = uuid.uuid4()
        self.black_card = self.deck.get_random_black()
        self.candidates.clear()

        for player in self.players.itervalues():
            player.has_submitted = False
            player.has_voted = False

        card_embed = discord.Embed(
            title="Black Card",
            description=self.black_card.text,
            color=support.Color.black(),
        )

        await self.thread.send(
            content=f"@everyone Pick {inflect.number_to_words(self.black_card.pick)} "
            f"white {inflect.plural('card', self.black_card.pick)} with "
            f"`/cah play`.",
            embed=card_embed,
        )

        await self.turn_timer()

    async def start_voting(self):
        self.turn_uuid = uuid.uuid4()
        self.is_voting = True

        msg = f"Vote for your favorite submission with `/cah play`."
        embed = discord.Embed(
            title="It's voting time!", description=msg, color=support.Color.mint()
        )

        for i, candidate in enumerate(self.candidates):
            embed.add_field(
                name=f"Submission {i + 1}", value=candidate.text, inline=True
            )
            if i + 1 % 3 == 0:
                embed.add_field(name="\u200b", value="\u200b", inline=False)

        await self.thread.send(content="@everyone", embed=embed)

        await self.turn_timer()

    # noinspection PyMethodOverriding
    async def submit_vote(
        self, candidate: cah.CAHCandidateCard, *, voter: cah.CAHPlayer
    ):
        real_candidate: cah.CAHCandidateCard = discord.utils.find(
            lambda c: c.uuid == candidate.uuid, self.candidates
        )
        real_candidate.voters.append(voter)

        if all(player.has_voted for player in self.players.itervalues()):
            # determine the highest vote total
            max_points = max(len(candidate.voters) for candidate in self.candidates)

            # get a list of candidates with the highest vote total
            potential_winners = [
                candidate
                for candidate in self.candidates
                if len(candidate.voters) == max_points
            ]

            # pick a winner at random from the aforementioned list. this is redundant if there is only one potential
            # winner, but fairly resolves ties in the event there are multiple potential winners
            await self.end_round(random.choice(potential_winners))

    async def turn_timer(self):
        async def play_callback():
            outstanding_players = [
                player
                for player in self.players.itervalues()
                if not player.has_submitted
            ]
            mentions = [player.user.mention for player in outstanding_players]
            msg = "The mentioned players have timed out. I've made their submissions for them."
            embed = discord.Embed(
                title="Time's up.", description=msg, color=support.Color.error()
            )
            await self.thread.send(content="".join(mentions), embed=embed)

            for player in outstanding_players:
                await player.increment_timeouts()

                if self.retrieve_player(player.user):
                    await player.force_pick()

        async def vote_callback():
            outstanding_players = [
                player
                for player in self.players.itervalues()
                if not player.has_submitted
            ]
            mentions = [player.user.mention for player in outstanding_players]

            msg = (
                "The mentioned players have timed out. I've cast their votes for them."
            )
            embed = discord.Embed(
                title="Time's up.", description=msg, color=support.Color.error()
            )
            await self.thread.send(content="".join(mentions), embed=embed)

            for player in outstanding_players:
                await player.increment_timeouts()

                if self.retrieve_player(player.user):
                    await player.force_vote()

        turn_uuid = self.turn_uuid

        await asyncio.sleep(self.settings.timeout)

        if turn_uuid == self.turn_uuid and self.retrieve_game(self.thread.id):
            await play_callback() if not self.is_voting else await vote_callback()


@define(frozen=True)
class CAHGameSettings:
    """
    Settings for a Cards Against Humanity game.
    """

    max_players: int
    points_to_win: int
    timeout: int
    use_czar: bool

    def __str__(self):
        players_str = (
            f"__**Maximum Players**: {self.max_players}__\n"
            f"Up to {self.max_players} can join this CAH game. Once that quota is filled, "
            f"no one else will be able to join unless a player leaves or is removed by the Game Host."
        )

        points_str = (
            f"__**Points to Win**: {self.points_to_win}__\n"
            f"The first player to reach {self.points_to_win} Awesome Points will win the game."
        )

        timeout_str = (
            f"__**Timeout**: {self.timeout} seconds__\n"
            f"Each player will have {self.timeout} seconds to play white cards when prompted. "
            f"When it's voting time, {'the Card Czar' if self.use_czar else 'players'} will have "
            f"{self.timeout} seconds to vote for a white card."
        )

        voting_str = (
            f"__**Voting Mode**: {'Card Czar' if self.use_czar else 'Popular Vote'}__\n"
            f"At the end of each round, the funniest submission will be decided by "
            f"{'a Card Czar' if self.use_czar else 'popular vote'}."
        )

        return "\n\n".join([players_str, points_str, timeout_str, voting_str])
