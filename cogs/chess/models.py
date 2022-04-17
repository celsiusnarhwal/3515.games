from __future__ import annotations

import asyncio
import random
from collections import Counter

import chess as pychess
import discord

import support
from cogs import chess
from support import posessive


class ChessGame:
    # TODO add turn timer
    # TODO create context verification decorator
    __all_games__ = dict()

    def __init__(self, players, thread: discord.Thread):
        self.thread = thread

        self.guild = thread.guild
        self.has_started = False
        self.players = [ChessPlayer(player, self) for player in players]
        self.current_player = None
        self.board = pychess.Board()

        random.shuffle(players)

        self.white = self.players[0]
        self.black = self.players[1]

        self.white.color = pychess.WHITE
        self.black.color = pychess.BLACK

        self.white.opponent = self.black
        self.black.opponent = self.white

        self.__all_games__[self.thread.id] = self

    async def game_timer(self):
        await asyncio.sleep(43200)

        if self.retrieve_game(self.thread.id):
            await self.force_close("time_limit")

    @classmethod
    def retrieve_game(cls, thread_id: int):
        return cls.__all_games__.get(thread_id)

    @classmethod
    def retrieve_duplicate_game(cls, players, guild) -> ChessGame:
        return discord.utils.find(
            lambda game: Counter([user.id for user in players]) == Counter(
                [player.user.id for player in game.players]) and game.guild == guild,
            cls.__all_games__.values()
        )

    def retrieve_player(self, user):
        return discord.utils.find(lambda player: player.user.id == user.id, self.players)

    async def force_close(self, reason: str):
        self.__all_games__.pop(self.thread.id)

        async def thread_deletion():
            for player in self.players:
                msg = f"Your chess match against {player.opponent} in {self.guild} was forced to end because " \
                      f"its game thread was deleted."

                embed = discord.Embed(title="Your chess match was forced to end.", description=msg,
                                      color=support.Color.red(), timestamp=discord.utils.utcnow())

                embed.set_footer(text=discord.utils.utcnow())

                await player.user.send(embed=embed)

        async def channel_deletion():
            for player in self.players:
                msg = f"Your chess match against {player.opponent} in {self.guild} was forced to end because " \
                      f"the parent channel of its game thread was deleted."

                embed = discord.Embed(title="Your chess match was forced to end.", description=msg,
                                      color=support.Color.red(), timestamp=discord.utils.utcnow())

                await player.user.send(embed=embed)

        async def time_limit():
            msg = "This chess match was forced to end because it took too long to complete.\n" \
                  "\n" \
                  "This thread has been locked and will be automatically deleted in 60 seconds."

            embed = discord.Embed(title="This chess match was forced to end.", description=msg,
                                  color=support.Color.red(), timestamp=discord.utils.utcnow())

            await self.thread.edit(name=f"{self.thread.name} - Game Over!")
            msg = await self.thread.send(embed=embed)
            await msg.pin()
            await self.thread.archive(locked=True)

            await asyncio.sleep(60)
            await self.thread.delete()

        reason_map = {
            "thread_deletion": thread_deletion(),
            "channel_deletion": channel_deletion(),
            "time_limit": time_limit(),
        }

        await reason_map[reason]

    async def open_lobby(self):
        msg = "Your chess match will take place in this thread.\n" \
              "\n" \
              "When you're ready, type `/chess ready`. When both players are ready, the match will begin.\n" \
              "\n" \
              "Spectators are welcome, but only the players will be permitted to talk in this thread.\n"

        embed = discord.Embed(title=f"Welcome, {self.players[0].user.name} and {self.players[1].user.name}.\n",
                              description=msg,
                              color=support.Color.mint())

        intro = await self.thread.send(embed=embed)
        await intro.pin()

    async def check_ready_players(self):
        if all(player.is_ready for player in self.players):
            await self.start_game()

    async def start_game(self):
        self.has_started = True

        msg = f"In chess, your objective is to checkmate your opponent's king. Accomplish this, and you win. Yes, " \
              f"it's really that simple.\n" \
              f"\n" \
              f"Players will have two minutes to move when its their turn. Fail to move in time, and I'll " \
              f"forfeit the match on your behalf.\n" \
              f"\n" \
              f"{self.white.user.mention} will play as **White**. {self.black.user.mention} will play as **Black**.\n" \
              f"\n" \
              f"Let's play!"

        embed = discord.Embed(title="Let's play chess!", description=msg, color=support.Color.mint())

        with chess.helpers.get_board_png(self.board) as board_png:
            embed.set_image(url=f"attachment://{board_png.filename}")
            await self.thread.send(embed=embed, file=board_png)

        await asyncio.sleep(3)

        await self.start_next_turn()

    async def start_next_turn(self):
        self.current_player = self.white if self.current_player != self.white else self.black

        embed = discord.Embed(title="New Turn", description=f"It's {posessive(self.current_player.user.name)}'s turn.",
                              color=self.current_player.get_embed_color())

        embed.set_thumbnail(url=self.current_player.user.display_avatar.url)

        await self.thread.send(content=f"{self.current_player.user.mention}, it's your turn.", embed=embed)

    async def end_game(self, reason: str, **kwargs):
        self.__all_games__.pop(self.thread.id)

        async def forfeit():
            forfeiter = kwargs.get("player")

            await self.thread.edit(name=f"{self.thread.name} - Game Over!")

            if self.has_started:
                winner = self.white if forfeiter.color == pychess.BLACK else self.black

                msg = f"{winner.user.mention} wins by forfeit.\n" \
                      f"\n" \
                      f"This thread will be automatically deleted in 60 seconds.\n" \
                      f"\n" \
                      f"Thanks for playing!"

                embed = discord.Embed(title=f"Chess: Game Over! {winner.user.name} wins!",
                                      description=msg,
                                      color=support.Color.mint())
            else:
                msg = f"{forfeiter.user.mention} forfeited the match, forcing it to end.\n" \
                      f"\n" \
                      f"This thread will be automatically deleted in 60 seconds."

                embed = discord.Embed(title="This chess match was forfeited.",
                                      description=msg,
                                      color=support.Color.red())

            forfeit_msg = await self.thread.send(embed=embed)
            await forfeit_msg.pin()

        async def draw():
            await self.thread.edit(name=f"{self.thread.name} - Game Over!")

            msg = "Both players agreed to a draw.\n" \
                  "\n" \
                  "This thread will be automatically deleted in 60 seconds.\n" \
                  "\n" \
                  "Thanks for playing!"

            embed = discord.Embed(title="Chess: Game Over! It's a draw!", description=msg, color=support.Color.mint())

            draw_msg = await self.thread.send(embed=embed)
            await draw_msg.pin()

        async def timeout():
            pass

        async def stalemate():
            pass

        async def checkmate():
            pass

        reason_map = {
            "forfeit": forfeit(),
            "draw": draw(),
            "timeout": timeout(),
            "stalemate": stalemate(),
            "checkmate": checkmate()
        }

        await reason_map[reason]

        await asyncio.sleep(60)
        await self.thread.delete()


class ChessPlayer:
    def __init__(self, user: discord.User, game: ChessGame):
        self.user = user
        self.game = game

        self.is_ready = False
        self.has_proposed_draw = False
        self.opponent = None
        self.color: pychess.Color = None

    async def ready(self):
        self.is_ready = True

        embed = discord.Embed(title=f"{self.user.name} is ready!",
                              description=f"{self.user.mention} is ready to play.",
                              color=support.Color.mint())

        await self.game.thread.send(embed=embed)

        await self.game.check_ready_players()

    async def move(self):
        pass

    async def forfeit(self):
        await self.game.end_game(reason="forfeit", player=self)

    async def propose_draw(self):
        if not any(player.has_proposed_draw for player in self.game.players):
            self.has_proposed_draw = True

            msg = f"{self.user.mention} proposes a draw. {self.opponent.user.mention} can agree to the proposal " \
                  f"by proposing a draw themselves or reject the proposal by doing nothing. "
            embed = discord.Embed(title="Draw Proposed", description=msg, color=support.Color.orange())
            await self.game.thread.send(embed=embed)
        else:
            msg = f"{self.user.mention} agrees to {self.opponent.user.mention}'s proposal to draw."
            embed = discord.Embed(title="Draw Agreed", description=msg, color=support.Color.green())
            await self.game.thread.send(embed=embed)

            await self.game.end_game(reason="draw")

    async def rescind_draw(self):
        self.has_proposed_draw = False

        msg = f"{self.user.mention} rescinds their proposal to draw."
        embed = discord.Embed(title="Draw Proposal Rescinded", description=msg, color=support.Color.greyple())
        await self.game.thread.send(embed=embed)

    def get_embed_color(self):
        embed_colors = {
            pychess.WHITE: support.Color.white(),
            pychess.BLACK: support.Color.black(),
        }

        return embed_colors[self.color]

    def __str__(self):
        return self.user.name
