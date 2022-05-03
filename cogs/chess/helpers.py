from __future__ import annotations

import os
from contextlib import contextmanager
from tempfile import TemporaryDirectory

import chess as pychess
import chess.svg as pychess_svg
import discord
from discord.ext import commands
from path import Path
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

import support
from cogs import chess


# decorators

def verify_context(level: str):
    """
    A decorator which implements a context verification system for chess matches. This system has four levels. In
    order, they are:

    - "thread" (verifies that the context is an chess game thread)
    - "player" (verifies that the invoker is a player in the chess mach)
    - "game" (verifies that the game has been started)
    - "turn" (verifies that it's the invoking players turn)

    Each verification level is inclusive of all previous ones, and *all* verification checks for the specified level
    must pass in order for the decorated command to execute.

    :param level: The verification level.
    """

    async def predicate(ctx: discord.ApplicationContext):
        command_name = f"`/{ctx.command.qualified_name}`"

        async def is_chess_thread():
            if chess.ChessGame.retrieve_game(ctx.channel.id):
                return True
            else:
                message = f"You can only use {command_name} in designated chess game threads. " \
                          f"Head to a game thread and try again."
                embed = discord.Embed(title="You can't do that here.", description=message,
                                      color=support.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        async def is_player():
            game = chess.ChessGame.retrieve_game(ctx.channel.id)

            if any(player.user == ctx.user for player in game.players):
                return True
            else:
                message = f"Only players in this chess match can use {command_name}."
                embed = discord.Embed(title="You're not playing in this match.", description=message,
                                      color=support.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        async def is_active_game():
            game = chess.ChessGame.retrieve_game(ctx.channel.id)

            if game.has_started:
                return True
            else:
                message = f"You can't use {command_name} until the match has begun. Wait until the match has begun, " \
                          f"then try again."
                embed = discord.Embed(title="This match hasn't started yet.", description=message,
                                      color=support.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        async def is_player_turn():
            game = chess.ChessGame.retrieve_game(ctx.channel.id)

            if game.current_player.user == ctx.user:
                return True
            else:
                message = f"You can only use {command_name} when it's your turn. Wait your turn, then try again."
                embed = discord.Embed(title="It's not your turn.", description=message,
                                      color=support.Color.red())
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        checks = {
            "chess_thread": is_chess_thread,
            "player": is_player,
            "game": is_active_game,
            "turn": is_player_turn,
        }

        success = False

        for key, check in checks.items():
            success = await check()

            if not success or key == level:
                break

        return success

    return commands.check(predicate)


# context managers


@contextmanager
def get_board_png(**kwargs) -> discord.File:
    with TemporaryDirectory() as tmp:
        with Path(tmp):
            open("board.svg", "w+").write(pychess_svg.board(**kwargs, size=1800))
            renderPM.drawToFile(svg2rlg("board.svg"), "board.png", fmt="png")
            yield discord.File(os.path.abspath("board.png"))


# miscellaneous


def convert_piece_format(piece: pychess.Piece | str | int, output: str) -> pychess.Piece | str | int:
    def from_piece():
        def to_symbol():
            return piece.symbol()

        def to_name():
            return pychess.PIECE_NAMES[to_int()]

        def to_int():
            return piece.piece_type

        return {
            "symbol": to_symbol(),
            "name": to_name(),
            "int": to_int()
        }[output]

    def from_symbol():
        def to_piece():
            return pychess.Piece.from_symbol(piece)

        def to_name():
            return pychess.PIECE_NAMES[to_int()]

        def to_int():
            return to_piece().piece_type

        return {
            "piece": to_piece(),
            "name": to_name(),
            "int": to_int()
        }[output]

    def from_name():
        def to_piece():
            return pychess.Piece.from_symbol(to_symbol())

        def to_symbol():
            return pychess.PIECE_SYMBOLS[pychess.PIECE_NAMES.index(piece)]

        def to_int():
            return to_piece().piece_type

        return {
            "piece": to_piece(),
            "symbol": to_symbol(),
            "int": to_int()
        }[output]

    def from_int():
        def to_piece():
            return pychess.Piece.from_symbol(to_symbol())

        def to_symbol():
            return pychess.PIECE_SYMBOLS[piece]

        def to_name():
            return pychess.PIECE_NAMES[piece]

        return {
            "piece": to_piece(),
            "symbol": to_symbol(),
            "name": to_name()
        }[output]

    if isinstance(piece, pychess.Piece):
        return from_piece()
    elif isinstance(piece, int):
        return from_int()

    elif isinstance(piece, str):
        if piece.casefold() in pychess.PIECE_SYMBOLS:
            return from_symbol()
        elif piece.casefold() in pychess.PIECE_NAMES:
            return from_name()
        else:
            raise ValueError(f"{piece} is not a valid piece")
    else:
        raise TypeError(f"piece must be a pychess.Piece, str, or int, not {type(piece)}")
