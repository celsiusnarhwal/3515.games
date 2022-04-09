from __future__ import annotations

import random

import chess
import discord
from llist import dllist as DoublyLinkedList

import support


class ChessGame:
    __all_games__ = dict()

    def __init__(self, players, thread: discord.Thread):
        self.thread = thread
        self.players = DoublyLinkedList([ChessPlayer(player, self) for player in players])

        random.shuffle(players)

        self.white = self.players.nodeat(0)
        self.black = self.players.nodeat(1)

        self.white.value.color = chess.WHITE
        self.black.value.color = chess.BLACK

        self.__all_games__[self.thread.id] = self

    async def open_lobby(self):
        msg = "Your chess game will take place in this thread.\n" \
              "\n" \
              "When you are ready, type `/chess ready`. When both players are ready, " \
              "the game will begin.\n" \
              "\n" \
              "Spectators are welcome, but only the players will be permitted to talk in this thread.\n"

        embed = discord.Embed(title=f"Welcome, {self.white.value.user.name} and {self.black.value.user.name}.\n",
                              description=msg,
                              color=support.Color.mint())

        intro = await self.thread.send(embed=embed)
        await intro.pin()


class ChessPlayer:
    def __init__(self, user: discord.User, game: ChessGame):
        self.user = user
        self.game = game

        self.color: chess.Color = None
