########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import random

import discord
import inflect as ifl
import support
from attr import define
from cogs import cah
from elysia import Fields
from support import BasePlayer, PlayerVoiceMixin

inflect = ifl.engine()


@define
class CAHPlayer(PlayerVoiceMixin, BasePlayer):
    """
    A player in a Cards Against Humanity game.

    Parameters
    ----------
    game: cah.CAHGame
        The game the player is in.

    Attributes
    ----------
    points: int
        The player's point total.
    consecutive_timeouts: int
        The number of consecutive times the player has timed out.
    hand: list[str]
        The white cards in the player's possession.
    has_submitted: bool
        Whether the player has made a submission for the current round.
    has_voted: bool
        Whether the player has cast a vote for the current round. Applicable only to popular vote games.
    terminable_views: list[cah.CAHTerminableView]
    """

    game: cah.CAHGame

    points: int = Fields.attr(default=0)
    consecutive_timeouts: int = Fields.attr(default=0)
    hand: list[cah.CAHCandidateCard] = Fields.attr(factory=list)
    has_submitted: bool = Fields.attr(default=False)
    has_voted: bool = Fields.attr(default=False)
    terminable_views: list[cah.CAHTerminableView] = Fields.attr(factory=list)

    async def show_hand(self, ctx: discord.ApplicationContext):
        """
        Shows the player the white cards they're currently holding.
        """
        embed = discord.Embed(
            title="Your White Cards",
            description=f"Here are the white cards you're currently holding:\n\n"
            f"{chr(10).join([f'- {card}' for card in self.hand])}",
            color=support.Color.white(),
        )

        await ctx.respond(embed=embed, ephemeral=True)

    async def pick_cards(self, ctx: discord.ApplicationContext):
        """
        Prompts the player to pick white cards to play.
        """
        candidate: cah.CAHCandidateCard = await cah.CAHCardSelectView(
            ctx=ctx, player=self
        ).select_card()

        if candidate:
            self.reset_timeouts()
            await self.submit_candidate(candidate)

    async def force_pick(self, player_removal: bool = False):
        """
        Pick random white cards on the player's behalf.

        Parameters
        ----------
        player_removal: bool
            Flags whether this is happening as a consequence of the player's removal from the game.
        """
        # pick x number of cards from the player's hand at random, depending on how many white cards need to be played
        cards = [
            self.hand[i]
            for i in random.sample(range(len(self.hand)), self.game.black_card.pick)
        ]

        # create candidates from those cards and randomly choose one of them to submit
        candidate: cah.CAHCandidateCard = random.choice(
            cah.CAHCandidateCard.create(self, *cards)
        )

        await self.submit_candidate(candidate, player_removal=player_removal)

    async def submit_candidate(
        self, candidate: cah.CAHCandidateCard, player_removal: bool = False
    ):
        """
        Submit a candidate card.

        Parameters
        ----------
        candidate: cah.CAHCandidateCard
            The candidate card to submit.
        player_removal: bool
            Flags whether this is happening automatically as a consequence of the player's removal from the game.
        """
        self.has_submitted = True

        if not player_removal:
            self.game.candidates.append(candidate)

        await self.terminate_views()

        for card in candidate.white_cards:
            self.hand.remove(card)

        self.add_cards(10 - len(self.hand))

        if all(
            player.has_submitted
            for player in self.game.players.itervalues()
            if player != self.game.card_czar.value
        ):
            await self.game.start_voting()

    async def vote(self, ctx: discord.ApplicationContext):
        """
        Prompt the player to vote for a candidate card.
        """
        selection: cah.CAHCandidateCard = await cah.CAHVotingView(
            ctx=ctx, game=self.game
        ).vote()

        if selection:
            self.has_voted = True
            self.reset_timeouts()
            await self.terminate_views()
            await self.game.submit_vote(candidate=selection, voter=self)

    async def force_vote(self):
        """
        Vote for a random candidate card on the player's behalf.
        """
        await self.terminate_views()
        await self.game.submit_vote(
            candidate=random.choice(self.game.candidates), voter=self
        )

    def add_cards(self, num_cards):
        """
        Add white cards to the player's hand.

        Parameters
        ----------
        num_cards: int
            The number of cards to add.
        """
        self.hand.extend(self.game.deck.get_random_white(num_cards))

    def get_ranking(self, with_string: bool = False) -> str:
        """
        Returns a string representation of the player's ranking in the game. (e.g. "1st", "2nd", "3rd", etc.).
        """
        leaderboard_group = discord.utils.find(
            lambda group: self in group, self.game.get_leaderboard()
        )
        ranking = inflect.ordinal(
            self.game.get_leaderboard().index(leaderboard_group) + 1
        )

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
