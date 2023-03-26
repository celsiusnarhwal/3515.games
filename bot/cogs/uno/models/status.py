########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import discord
from attr import define
from cogs import uno
from cogs.uno.models import inflect
from elysia import Fields
from keyboard import *
from sortedcontainers import SortedKeyList


@define
class UnoStatusTracker:
    """
    Tracks game statistics.
    """

    game: uno.UnoGame

    num_turns: int = Fields.attr(default=0)
    total_cards_played: int = Fields.attr(default=0)
    total_cards_drawn: int = Fields.attr(default=0)
    previous_turn_record: list[discord.Embed] = Fields.attr(factory=list)

    def get_game_settings(self) -> str:
        """
        Returns a string representation of the game settings.
        """
        return str(self.game.settings)

    def get_player_list(self) -> Iterator[uno.UnoPlayer]:
        """
        Returns an iterator over of all players in the game.
        """
        return self.game.players.itervalues()

    async def get_turn_order(self) -> list[uno.UnoPlayer]:
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

    def get_leaderboard(self) -> list[list[uno.UnoPlayer]]:
        """
        Returns a list of all players in the game, sorted in descending order by score.

        Notes
        -----
        To be more precise,
        this method returns a list of lists of :class:`uno.UnoPlayer` objects - players who have the same score
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
        player: :class:`uno.UnoPlayer`
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

    def get_player_stats(self, player: uno.UnoPlayer) -> dict:
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
