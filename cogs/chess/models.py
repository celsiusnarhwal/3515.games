from __future__ import annotations

import asyncio
import random

import chess as pychess
import discord
from llist import dllist as DoublyLinkedList

import support
from cogs import chess


class ChessGame:
    __all_games__ = dict()

    def __init__(self, players, thread: discord.Thread):
        self.thread = thread

        self.players = DoublyLinkedList([ChessPlayer(player, self) for player in players])
        self.board = pychess.Board()
        self.has_started = False

        random.shuffle(players)

        self.white = self.players[0]
        self.black = self.players[1]

        self.white.color = pychess.WHITE
        self.black.color = pychess.BLACK

        self.white.opponent = self.black
        self.black.opponent = self.white

        self.__all_games__[self.thread.id] = self

    @classmethod
    def retrieve_game(cls, thread_id: int):
        return cls.__all_games__.get(thread_id)

    def retrieve_player(self, user, return_node=False):
        if return_node:
            return discord.utils.find(lambda node: node.value.user.id == user.id, self.players.iternodes())
        else:
            return discord.utils.find(lambda player: player.user.id == user.id, self.players.itervalues())

    async def open_lobby(self):
        msg = "Your chess game will take place in this thread.\n" \
              "\n" \
              "When you're ready, type `/chess ready`. When both players are ready, the game will begin.\n" \
              "\n" \
              "Spectators are welcome, but only the players will be permitted to talk in this thread.\n"

        embed = discord.Embed(title=f"Welcome, {self.players[0].user.name} and {self.players[1].user.name}.\n",
                              description=msg,
                              color=support.Color.mint())

        intro = await self.thread.send(embed=embed)
        await intro.pin()

    async def check_ready_players(self):
        if all(player.is_ready for player in self.players.itervalues()):
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

        with chess.get_board_png(self.board) as board_png:
            embed.set_image(url=f"attachment://{board_png.filename}")
            await self.thread.send(embed=embed, file=board_png)

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
                                      description=msg)
            else:
                msg = f"{forfeiter.user.mention} has forfeited the game, forcing it to end.\n" \
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

            embed = discord.Embed(title="Chess: Game Over!", description=msg, color=support.Color.mint())

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

            msg = f"{self.user.mention} has proposed a draw. {self.opponent.user.mention} can agree to the proposal " \
                  f"by using `/chess draw propose` or reject the proposal by doing nothing. "
            embed = discord.Embed(title="Draw Proposed", description=msg, color=support.Color.orange())

            await self.game.thread.send(embed=embed)
        else:
            await self.game.end_game(reason="draw")

    async def rescind_draw(self):
        self.has_proposed_draw = False

        msg = f"{self.user.mention} has rescinded their proposal to draw."
        embed = discord.Embed(title="Draw Proposal Rescinded", description=msg, color=support.Color.greyple())

        await self.game.thread.send(embed=embed)
