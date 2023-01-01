########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import os
import random

import discord

import support
from cogs import rps


class RPSGame:
    """
    Represents a Rock-Paper-Scissors match.
    """

    def __init__(self, players: list[RPSPlayer], game_format: str, points_to_win: int):
        """
        The constructor for `RPSGame`.

        :param players: A list of the game's players.
        :param game_format: The format of the game; "Best of Three", "Best of Five", or "Best of Nine".
        :param points_to_win: The number of points needed to win the game. The game will end as soon as one player
        reaches this many points.
        """
        self.players = players
        self.points_to_win = points_to_win
        self.game_format = game_format
        self.challenger = players[0]
        self.opponent = players[1]
        self.current_round = 1
        self.match_record = [[]]

    async def issue_challenge(self, ctx: discord.ApplicationContext):
        """
        This function handles the actual background work of issuing a challenge to a user.

        :param ctx: An ApplicationContext object.
        :return: True if the challenge recipient accepts the challenge, False otherwise.
        """

        # confirm with the challenger (i.e. the invoker of /rps challenge) that they want to issue the challenge
        view = support.ConfirmationView(ctx=ctx)
        challenge_confirmation = await view.request_confirmation(
            prompt_text=f"Challenge {self.opponent.user.mention} to Rock-Paper-Scissors ({self.game_format})?",
            ephemeral=True
        )

        if challenge_confirmation:
            await ctx.interaction.edit_original_message(content=f"Waiting on {self.opponent.user.mention}...",
                                                        view=None)

            # ask the challenge recipient whether they accept the challenge
            view = support.GameChallengeResponseView(ctx=ctx,
                                                     target_user=self.opponent.user,
                                                     challenger=self.challenger.user,
                                                     game_name=f"Rock-Paper-Scissors ({self.game_format})"
                                                     )

            view.timeout = 60
            challenge_acceptance = await view.request_response()

            if challenge_acceptance:
                return True
        else:
            if challenge_confirmation is not None:
                await ctx.interaction.edit_original_message(content="Okay! Your challenge was canceled.", view=None)
                return False

    async def game_intro(self, ctx):
        """
        Announces the start of a Rock-Paper-Scissors match.

        :param ctx: An ApplicationContext object.
        """
        game_intro_text = f"**Players:** {self.challenger.user.mention} vs." \
                          f" {self.opponent.user.mention}\n" \
                          f"**Rules:** {self.game_format} (first player to {self.points_to_win} points wins)\n" \
                          f"\n" \
                          f"Let's play!"

        intro_embed = discord.Embed(title="Rock-Paper-Scissors: Game Start!", description=game_intro_text,
                                    color=support.Color.mint())

        with support.Assets.rps():
            intro_gif = random.choice(os.listdir("intro_gifs"))
            gif_file = discord.File(os.path.join("intro_gifs", intro_gif), filename=intro_gif)
            intro_embed.set_image(url=f"attachment://{intro_gif}")

            await ctx.send(embed=intro_embed, file=gif_file)

    async def select_player_moves(self, ctx):
        """
        Prompts both players to select their moves.

        :param ctx: An ApplicationContext object.
        :return: True if move selection completed successfully, False otherwise.
        """
        return await rps.RPSChooseMoveView(ctx=ctx, players=self.players).start_move_selection(
            round_number=self.current_round)

    async def report_round_results(self, ctx):
        """
        Announces the results of a round and adds them to the game's match record.

        :param ctx: An ApplicationContext object.
        """

        # dictionary of winning cases for rock-paper-scissors, where they key "beats" the value. rock beats scissors,
        # scissors beats paper, paper beats rock.
        winning_cases = {
            "Rock": "Scissors",
            "Scissors": "Paper",
            "Paper": "Rock",
        }

        # if both players selected the same move, it's a draw.
        if self.challenger.selected_move == self.opponent.selected_move:
            result = "It's a draw."
        else:
            # if the winning case for the challenger's move is the opponent's move, the challenger wins.
            if winning_cases[self.challenger.selected_move] == self.opponent.selected_move:
                winner = self.challenger
            else:
                # if it's not a draw and the challenger doesn't win, the opponent wins.
                winner = self.opponent

            winner.score += 1
            result = f"{winner.user.mention} wins."

        results_text = f"{self.challenger.user.mention} plays **{self.challenger.selected_move}**.\n" \
                       f"{self.opponent.user.mention} plays **{self.opponent.selected_move}**.\n" \
                       f"\n" \
                       f"**Result:** {result}\n" \
                       f"\n" \
                       f"**Score:** {self.challenger.user.mention} {self.challenger.score} - " \
                       f"{self.opponent.score} {self.opponent.user.mention}"

        results_embed = discord.Embed(title=f"Round {self.current_round} Results", description=results_text,
                                      color=support.Color.mint())

        # each page in the match record can contain the results of up to three rounds. this limitation, and the
        # implementation of pagination in the match record to begin with, aims to prevent the match record from
        # exceeding Discord's character limit when its sent as an embed in chat.
        if len(self.match_record[-1]) < 3:
            self.match_record[-1].append(f"**__{results_embed.title}__**\n\n{results_embed.description}")
        else:
            self.match_record.append([f"**__{results_embed.title}__**\n\n{results_embed.description}"])

        await ctx.send(embed=results_embed)

        # clears selected moves for both players to prepare for the next round
        self.challenger.clear_selected_move()
        self.opponent.clear_selected_move()

    def check_for_match_winner(self):
        """
        Checks to see whether a player has reached the point threshold for victory. This is called after every round.

        :return: The victorious player if applicable, otherwise None.
        """
        return next((player for player in self.players if player.score == self.points_to_win), None)

    async def end_match(self, ctx, winner: RPSPlayer):
        """
        Ends a Rock-Paper-Scissors game. This is only called when a player has reached the point threshold for victory.

        :param ctx: An ApplicationContext object.
        :param winner: The winner of the match.
        """
        self.match_record[-1].append(f"**Match Winner:** {winner.user.mention}")

        await rps.RPSMatchEndView(ctx=ctx, match_record=self.match_record).show_match_results(players=self.players,
                                                                                              winner=winner)


class RPSPlayer:
    """
    Represents a player in a Rock-Paper-Scissors match.
    """

    def __init__(self, user: discord.User):
        """
        The constructor for `RPSPlayer`.
        :param user: The user to construct a player from.
        """
        self.user = user
        self.selected_move = None
        self.score = 0

    def clear_selected_move(self):
        """
        Clears the user's selected move.
        """
        self.selected_move = None
