########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

from contextlib import asynccontextmanager
from tempfile import TemporaryDirectory

import chess.svg
import discord
from discord.ext import commands
from path import Path
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

import support
from cogs import shogi

# decorators


def verify_context(level: str):
    async def predicate(ctx: discord.ApplicationContext):
        command_name = f"`/{ctx.command.qualified_name}`"

        async def is_chess_thread():
            if shogi.ChessGame.retrieve_game(ctx.channel.id):
                return True
            else:
                message = (
                    f"You can only use {command_name} in designated chess game threads. "
                    f"Head to a game thread and try again."
                )
                embed = discord.Embed(
                    title="You can't do that here.",
                    description=message,
                    color=support.Color.error(),
                )
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        async def is_player():
            game = shogi.ChessGame.retrieve_game(ctx.channel.id)

            if any(player.user == ctx.user for player in game.players):
                return True
            else:
                message = f"Only players in this chess game can use {command_name}."
                embed = discord.Embed(
                    title="You're not playing in this game.",
                    description=message,
                    color=support.Color.error(),
                )
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        async def is_active_game():
            game = shogi.ChessGame.retrieve_game(ctx.channel.id)

            if game.has_started:
                return True
            else:
                message = (
                    f"You can't use {command_name} until the game has begun. Wait until the game has begun, "
                    f"then try again."
                )
                embed = discord.Embed(
                    title="This game hasn't started yet.",
                    description=message,
                    color=support.Color.error(),
                )
                await ctx.respond(embed=embed, ephemeral=True)

                return False

        async def is_player_turn():
            game = shogi.ChessGame.retrieve_game(ctx.channel.id)

            if game.current_player.user == ctx.user:
                return True
            else:
                message = f"You can only use {command_name} when it's your turn. Wait your turn, then try again."
                embed = discord.Embed(
                    title="It's not your turn.",
                    description=message,
                    color=support.Color.error(),
                )
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


@asynccontextmanager
async def get_board_image(**kwargs) -> discord.File:
    with (TemporaryDirectory() as tmp, Path(tmp)):
        open("board.svg", "w+").write(chess.svg.board(**kwargs, size=1800))
        renderPM.drawToFile(svg2rlg("board.svg"), "board.png", fmt="png")
        yield discord.File(Path("board.png").abspath())
