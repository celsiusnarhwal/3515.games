########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import asyncio
import math
import random
import uuid
from collections import Counter
from contextlib import asynccontextmanager

import discord
from attrs import define
from elysia import Fields
from pydantic import BaseModel, validate_arguments

import chess as pychess
import shrine
import support
from chess import square_name
from cogs import chess
from keyboard import *
from shrine.kami import posessive
from support import BasePlayer, ThreadedGame


@define(slots=False)
class ChessGame(ThreadedGame):
    __games__: ClassVar[dict[int, Self]] = {}

    players: list[ChessPlayer] = Fields.field()
    saving_enabled: bool = Fields.field(frozen=True)

    has_started: bool = Fields.attr(default=False)
    current_player: ChessPlayer = Fields.attr(default=None)
    turn_number: int = Fields.attr(default=0)
    turn_uuid: uuid.UUID = Fields.attr(default=None)
    white: ChessPlayer = Fields.attr(default=None)
    black: ChessPlayer = Fields.attr(default=None)
    turn_record: discord.Embed = Fields.attr(default=None)

    def __attrs_post_init__(self):
        super().__attrs_post_init__()

        self.board: ChessBoard = ChessBoard()
        self.processor = ChessEventProcessor(self)
        self.players = [ChessPlayer(player, self) for player in self.players]

        for player in self.players:
            player.set_opponent()

    async def game_timer(self):
        await asyncio.sleep(60**2 * 8)

        if self.retrieve_game(self.thread.id):
            await self.force_close("time_limit")

    @classmethod
    def retrieve_duplicate_game(cls, players, guild) -> Self:
        return discord.utils.find(
            lambda game: Counter([user.id for user in players])
            == Counter([player.user.id for player in game.players])
            and game.guild == guild,
            cls.__games__.values(),
        )

    def retrieve_player(self, user):
        return discord.utils.find(
            lambda player: player.user.id == user.id, self.players
        )

    async def force_close(self, reason: str):
        self.kill()

        async def thread_deletion():
            for player in self.players:
                msg = (
                    f"Your chess match against {player.opponent.user.mention} in {self.guild} "
                    f"was forced to end because its game thread was deleted."
                )

                embed = discord.Embed(
                    title="Your chess match was forced to end.",
                    description=msg,
                    color=support.Color.error(),
                    timestamp=discord.utils.utcnow(),
                )

                await player.user.send(embed=embed)

        async def channel_deletion():
            for player in self.players:
                msg = (
                    f"Your chess match against {player.opponent.user.mention} in {self.guild} was forced to "
                    f"end because the parent channel of its game thread was deleted."
                )

                embed = discord.Embed(
                    title="Your chess match was forced to end.",
                    description=msg,
                    color=support.Color.error(),
                    timestamp=discord.utils.utcnow(),
                )

                await player.user.send(embed=embed)

        async def time_limit():
            msg = (
                "This chess match was forced to end because it took too long to complete.\n"
                "\n"
                "This thread has been locked and will be automatically deleted in 60 seconds."
            )

            embed = discord.Embed(
                title="This chess match was forced to end.",
                description=msg,
                color=support.Color.error(),
                timestamp=discord.utils.utcnow(),
            )

            await self.thread.edit(name=f"{self.thread.name} - Game Over!")
            msg = await self.thread.send(embed=embed)
            await msg.pin()
            await self.thread.archive(locked=True)

            await asyncio.sleep(60)
            await self.thread.delete()

        reason_map = {
            "thread_deletion": thread_deletion,
            "channel_deletion": channel_deletion,
            "time_limit": time_limit,
        }

        await reason_map[reason]()

    async def open_lobby(self):
        msg = (
            "Your chess game will take place in this thread.\n"
            "\n"
            "When you're ready, type `/chess ready`. When both players are ready, the game will begin.\n"
        )

        embed = discord.Embed(
            title=f"Hi, {self.players[0].user.name} and {self.players[1].user.name}!\n",
            description=msg,
            color=support.Color.mint(),
        )

        if self.saving_enabled:
            embed.set_footer(text="Game saving is enabled.")
        else:
            embed.set_footer(text="Game saving is disabled.")

        intro = await self.thread.send(embed=embed)
        await intro.pin()

    async def check_ready_players(self):
        if all(player.is_ready for player in self.players):
            await self.start_game()

    async def start_game(self):
        self.has_started = True

        random.shuffle(self.players)

        self.white = self.players[0]
        self.black = self.players[1]

        for player in self.players:
            player.set_color()

        await self.thread.edit(
            name=f"Chess - {self.white.user.name} vs. {self.black.user.name}"
        )

        with shrine.Torii.chess() as torii:
            template = torii.get_template("game-start.md")
            msg = template.render(
                white=self.white.user.mention, black=self.black.user.mention
            )

        embed = discord.Embed(
            title="Let's play chess!", description=msg, color=support.Color.mint()
        )

        async with self.thread.typing():
            async with self.board.image() as board_png:
                embed.set_image(url=f"attachment://{board_png.filename}")
                await self.thread.send(embed=embed, file=board_png)

        await asyncio.sleep(3)

        await self.start_next_turn()

    async def start_next_turn(self):
        self.turn_number += 1
        self.turn_uuid = uuid.uuid4()

        self.current_player = (
            self.white if self.current_player != self.white else self.black
        )

        embed = discord.Embed(
            title="New Turn",
            description=f"It's {posessive(self.current_player.user.name)} turn.",
            color=self.current_player.embed_color(),
        )

        embed.set_thumbnail(url=self.current_player.user.display_avatar.url)

        await self.thread.send(
            content=f"{self.current_player.user.mention}, it's your turn.", embed=embed
        )

        await self.turn_timer()

    async def end_current_turn(self):
        self.turn_uuid = None

        async with self.thread.typing():
            async with self.board.image() as board_png:
                self.turn_record.set_image(url=f"attachment://{board_png.filename}")
                await self.thread.send(embed=self.turn_record, file=board_png)

        if self.board.is_checkmate():
            await self.end_game(reason="checkmate", winner=self.current_player)
        elif self.board.is_stalemate():
            await self.end_game(reason="stalemate")
        else:
            await self.start_next_turn()

    async def turn_timer(self):
        turn_uuid = self.turn_uuid

        await asyncio.sleep(90)
        if turn_uuid == self.turn_uuid and self.retrieve_game(self.thread.id):
            msg = f"{self.current_player.user.mention} has 30 seconds left to move."
            embed = discord.Embed(
                title="30 Second Warning",
                description=msg,
                color=support.Color.caution(),
            )
            await self.thread.send(embed=embed)

            await asyncio.sleep(30)
            if turn_uuid == self.turn_uuid and self.retrieve_game(self.thread.id):
                msg = f"{self.current_player.user.mention} took too long to move."
                embed = discord.Embed(
                    title=f"{self.current_player.user.name} timed out.",
                    description=msg,
                    color=support.Color.error(),
                )
                await self.thread.send(embed=embed)

                await self.end_game(reason="timeout", player=self.current_player)

    async def end_game(self, reason: str, **kwargs):
        self.kill()

        async def forfeit():
            forfeiter: ChessPlayer = kwargs.get("player")

            await self.thread.edit(name=f"{self.thread.name} - Game Over!")

            if self.has_started:
                winner = forfeiter.opponent

                msg = f"{winner.user.mention} wins by forfeit."

                return discord.Embed(
                    title=f"Game Over! {winner.user.name} wins!",
                    description=msg,
                    color=support.Color.mint(),
                )
            else:
                msg = (
                    f"{forfeiter.user.mention} forfeited the match, forcing it to end.\n"
                    f"\n"
                    f"This thread will be automatically deleted in 60 seconds."
                )

                embed = discord.Embed(
                    title="This chess match was forfeited.",
                    description=msg,
                    color=support.Color.error(),
                )

                forfeit_msg = await self.thread.send(embed=embed)
                await forfeit_msg.pin()

        async def draw():
            await self.thread.edit(name=f"{self.thread.name} - Game Over!")

            msg = "Both players agreed to a draw."

            return discord.Embed(
                title="Game Over! It's a draw!",
                description=msg,
                color=support.Color.mint(),
            )

        async def timeout():
            offender: ChessPlayer = kwargs.get("player")

            msg = (
                f"You took too long to move in your chess match against {offender.opponent.user.mention} in "
                f"{self.guild}. I have forfeited the match on your behalf, and {offender.opponent.user.name} has "
                f"won on time."
            )
            embed = discord.Embed(
                title="You timed out.",
                description=msg,
                color=support.Color.error(),
                timestamp=discord.utils.utcnow(),
            )
            await offender.user.send(embed=embed)

            await self.thread.edit(name=f"{self.thread.name} - Game Over!")

            msg = f"{offender.opponent.user.mention} wins on time."

            return discord.Embed(
                title=f"Game Over! {offender.opponent.user.name} wins!",
                description=msg,
                color=support.Color.mint(),
            )

        async def stalemate():
            msg = "The match ended in a stalemate."

            return discord.Embed(
                title="Chess: Game Over! It's a draw!",
                description=msg,
                color=support.Color.mint(),
            )

        async def checkmate():
            winner = kwargs.get("winner")

            msg = f"{winner.user.mention} wins by checkmate. Congratulations!"

            return discord.Embed(
                title=f"Game Over! {winner.user.name} wins!",
                description=msg,
                color=support.Color.mint(),
            )

        reason_map = {
            "forfeit": forfeit,
            "draw": draw,
            "timeout": timeout,
            "stalemate": stalemate,
            "checkmate": checkmate,
        }

        embed_to_send = await reason_map[reason]()

        if embed_to_send:
            if self.saving_enabled and self.board.move_stack:
                embed_to_send.description += (
                    f"\n\nPlayers can save a record of this game with the Save Game button "
                    f"below and revisit it at any time via `/chess replay`."
                )

            embed_to_send.description += (
                f"\n\nThis thread will be automatically deleted in 60 seconds.\n"
                f"\n"
                f"Thanks for playing!"
            )

            view = chess.ChessEndgameView(game=self) if self.saving_enabled else None

            message = await self.thread.send(embed=embed_to_send, view=view)

            await message.pin()

        await asyncio.sleep(60)
        await self.thread.delete()


@define
class ChessPlayer(BasePlayer):
    game: ChessGame

    is_ready: bool = Fields.attr(default=False)
    opponent: ChessPlayer = Fields.attr(default=None)
    has_proposed_draw: bool = Fields.attr(default=False)
    color: pychess.Color = Fields.attr(default=None)
    piece_symbols: list[str] = Fields.attr(default=None)

    async def ready(self):
        self.is_ready = True

        embed = discord.Embed(
            title=f"{self.user.name} is ready!",
            description=f"{self.user.mention} is ready to play.",
            color=support.Color.mint(),
        )

        await self.game.thread.send(embed=embed)

        await self.game.check_ready_players()

    async def move_with_gui(self, ctx: discord.ApplicationContext):
        view = chess.ChessMoveView(ctx=ctx, player=self)

        move = await view.start()

        self.game.board.push(move)

        self.game.processor.move_event(player=self, move=move, data=view.move_data)

        await self.end_turn()

    async def move_with_notation(self, ctx: discord.ApplicationContext, notation: str):
        def parse_move(move_str: str) -> pychess.Move | None:
            try:
                parsed_move = self.game.board.parse_san(move_str)
            except ValueError:
                try:
                    parsed_move = self.game.board.parse_uci(move_str)
                except ValueError:
                    return None

            return parsed_move if self.game.board.is_legal(parsed_move) else None

        move = parse_move(notation)

        if move:
            await ctx.respond("Making move...", ephemeral=True)

            self.game.board.push(move)

            board_copy = self.game.board.copy()
            board_copy.pop()

            # not using construct() here causes a bizarre ConfigError with pydantic so we'll just have to cope for now
            move_data = ChessMoveData.construct(
                piece=board_copy.piece_at(move.from_square),
                origin=move.from_square,
                destination=move.to_square,
                promotion=ChessPiece.from_piece_type(move.promotion, self.color),
            )

            self.game.processor.move_event(player=self, move=move, data=move_data)

            await self.end_turn()
        else:
            msg = (
                "The move you entered is invalid. You must enter a valid move using either algebraic or "
                "Universal Chess Interface (UCI) notation. If you're confused, use `/chess move` without "
                "specifying the `move` option to make a move using the graphical interface."
            )

            embed = discord.Embed(
                title="Invalid Move", description=msg, color=support.Color.error()
            )

            await ctx.respond(embed=embed, ephemeral=True)

    async def view_board(self, ctx: discord.ApplicationContext):
        view = chess.ChessBoardView(ctx=ctx, player=self)
        await view.initiate_view()

    async def forfeit(self):
        await self.game.end_game(reason="forfeit", player=self)

    async def propose_draw(self):
        if not any(player.has_proposed_draw for player in self.game.players):
            self.has_proposed_draw = True

            msg = (
                f"{self.mention} proposes a draw. {self.opponent.mention} can agree to the proposal "
                f"by proposing a draw {self.opponent.pronoun('themselves')} or reject the proposal by doing nothing. "
            )
            embed = discord.Embed(
                title="Draw Proposed", description=msg, color=support.Color.caution()
            )
            await self.game.thread.send(embed=embed)
        else:
            msg = f"{self.user.mention} agrees to {self.opponent.user.mention}'s proposal to draw."
            embed = discord.Embed(
                title="Draw Agreed", description=msg, color=support.Color.green()
            )
            await self.game.thread.send(embed=embed)

            await self.game.end_game(reason="draw")

    async def rescind_draw(self):
        self.has_proposed_draw = False

        msg = f"{self.mention} rescinds {self.pronoun('their')} proposal to draw."
        embed = discord.Embed(
            title="Draw Proposal Rescinded",
            description=msg,
            color=support.Color.greyple(),
        )
        await self.game.thread.send(embed=embed)

    async def end_turn(self):
        await self.game.end_current_turn()

    def set_color(self):
        self.color = pychess.WHITE if self == self.game.white else pychess.BLACK

    def embed_color(self):
        embed_colors = {
            pychess.WHITE: support.Color.white(),
            pychess.BLACK: support.Color.black(),
        }

        return embed_colors[self.color]

    def set_opponent(self):
        self.opponent = discord.utils.find(lambda p: p is not self, self.game.players)

    def __str__(self):
        return self.user.name


class ChessBoard(pychess.Board):
    def piece_at(self, square) -> ChessPiece | None:
        piece = super().piece_at(square)
        return ChessPiece.from_base_piece(piece) if piece else None

    @asynccontextmanager
    async def image(self) -> discord.File:
        async with chess.get_board_image(board=self) as image:
            yield image


class ChessPiece(pychess.Piece):
    def name(self) -> str:
        return pychess.PIECE_NAMES[self.piece_type]

    @classmethod
    def from_base_piece(cls, piece: pychess.Piece) -> ChessPiece:
        return cls(piece.piece_type, piece.color)

    @classmethod
    def from_piece_type(cls, piece_type: int, color: int) -> ChessPiece:
        return cls(piece_type, color)

    @classmethod
    def from_symbol(cls, symbol: str) -> ChessPiece:
        try:
            return super().from_symbol(symbol) if symbol is not None else None
        except AttributeError:
            return None

    def __str__(self):
        return self.unicode_symbol() + self.name().capitalize()

    def __eq__(self, other):
        return self.symbol() == other.symbol()


class ChessMoveData(BaseModel):
    piece: ChessPiece = None
    origin: int = 0
    destination: int = 0
    promotion: ChessPiece = None

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)


@define(frozen=True)
class ChessEventProcessor:
    game: ChessGame

    @validate_arguments(config=dict(arbitrary_types_allowed=True))
    def move_event(self, player: ChessPlayer, move: pychess.Move, data: ChessMoveData):
        msg = (
            f"**{player.user.mention}** moves **{data.piece}** from {square_name(data.origin).capitalize()} "
            f"to {square_name(data.destination).capitalize()}."
        )

        embed = discord.Embed(
            title="Piece Moved", description=msg, color=player.embed_color()
        )

        embed.set_footer(
            icon_url=player.user.display_avatar.url,
            text=f"{player.user} • {self.game.thread.name} • Turn {math.ceil(self.game.turn_number / 2)}",
        )

        self.game.turn_record = embed

        if move.promotion:
            self.promotion_event(self, data)

        board_copy = self.game.board.copy(stack=1)
        board_copy.pop()

        if board_copy.is_castling(move):
            self.castle_event(player)
        if board_copy.is_capture(move):
            self.capture_event(player)

        if self.game.board.is_checkmate():
            self.checkmate_event(player.opponent)
        elif self.game.board.is_stalemate():
            self.stalemate_event()
        elif self.game.board.is_check():
            self.check_event(player.opponent)

    def promotion_event(self, player: ChessPlayer, data: ChessMoveData):
        msg = (
            f"**{player.user.name}** promotes "
            f"**{ChessPiece.from_symbol(data.piece)} ({square_name(data.destination).capitalize()})** "
            f"to a {ChessPiece.from_symbol(data.promotion)}."
        )

        self.game.turn_record.add_field(name="Pawn Promoted", value=msg, inline=False)

    def castle_event(self, player: ChessPlayer):
        msg = f"**{player.user.name}** castles."

        self.game.turn_record.add_field(
            name="Castle Performed", value=msg, inline=False
        )

    def capture_event(self, player: ChessPlayer):
        board_copy = self.game.board.copy()
        move = board_copy.pop()

        square = discord.utils.find(
            lambda sq: board_copy.piece_at(sq)
            and (
                board_copy.piece_at(sq).piece_type == pychess.PAWN
                or not board_copy.is_en_passant(move)
            )
            and board_copy.color_at(sq) is not player.color,
            [move.to_square, move.to_square - 8, move.to_square + 8],
        )

        captured_piece = board_copy.piece_at(square)

        msg = (
            f"**{player.user.name}** captures {player.opponent.user.mention}'s **{captured_piece} "
            f"({square_name(move.to_square).capitalize()})**"
        )

        if board_copy.is_en_passant(move):
            msg += " *en passant*"

        msg += "."

        self.game.turn_record.add_field(name="Piece Captured", value=msg, inline=False)

    def check_event(self, player: ChessPlayer):
        msg = f"**{player.user.name}** is in check."

        self.game.turn_record.add_field(name="Check", value=msg, inline=False)

    def checkmate_event(self, player: ChessPlayer):
        msg = f"{player.user.mention} is in checkmate."

        self.game.turn_record.add_field(name="Checkmate", value=msg, inline=False)

    def stalemate_event(self):
        msg = "The match reaches a stalemate."

        self.game.turn_record.add_field(name="Stalemate", value=msg, inline=False)
