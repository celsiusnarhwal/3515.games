from __future__ import annotations

import asyncio
import random
import uuid
from collections import Counter

import chess as pychess
import discord
from chess import square_name
from llist import dllist as DoublyLinkedList

import support
from cogs import chess
from support import posessive


class ChessGame:
    __all_games__ = dict()

    def __init__(self, players, thread: discord.Thread):
        self.thread = thread

        self.guild = thread.guild
        self.has_started = False
        self.players = [ChessPlayer(player, self) for player in players]
        self.current_player = None
        self.turn_uuid = None
        self.board = pychess.Board()
        self.move_history = DoublyLinkedList([self.board.copy()])
        self.turn_record: discord.Embed = None

        for player in self.players:
            player.opponent = self.players[0] if player == self.players[1].user else \
                self.players[1]

        self.white = None
        self.black = None

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
                msg = f"Your chess match against {player.opponent.user.mention} in {self.guild} " \
                      f"was forced to end because its game thread was deleted."

                embed = discord.Embed(title="Your chess match was forced to end.", description=msg,
                                      color=support.Color.red(), timestamp=discord.utils.utcnow())

                await player.user.send(embed=embed)

        async def channel_deletion():
            for player in self.players:
                msg = f"Your chess match against {player.opponent.user.mention} in {self.guild} was forced to " \
                      f"end because the parent channel of its game thread was deleted."

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
            "thread_deletion": thread_deletion,
            "channel_deletion": channel_deletion,
            "time_limit": time_limit,
        }

        await reason_map[reason]()

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

        random.shuffle(self.players)

        self.white = self.players[0]
        self.black = self.players[1]

        for player in self.players:
            player.populate_color_based_metadate()

        msg = f"In chess, your objective is to checkmate your opponent's king. Accomplish this, and you win. Yes, " \
              f"it's really that simple.\n" \
              f"\n" \
              f"When it's your turn, make a move with `/chess move`. When it's not your turn (or even when it is " \
              f"your turn), you can view the board and move history with `/chess board`.\n" \
              f"\n" \
              f"Players will have two minutes to move when its their turn. Fail to move in time, and I'll " \
              f"forfeit the match on your behalf.\n" \
              f"\n" \
              f"{self.white.user.mention} will play as **White**. {self.black.user.mention} will play as **Black**.\n" \
              f"\n" \
              f"Let's play!"

        embed = discord.Embed(title="Let's play chess!", description=msg, color=support.Color.mint())

        async with self.thread.typing():
            with chess.helpers.get_board_png(board=self.board) as board_png:
                embed.set_image(url=f"attachment://{board_png.filename}")
                await self.thread.send(embed=embed, file=board_png)

        await asyncio.sleep(3)

        await self.start_next_turn()

    async def start_next_turn(self):
        self.turn_uuid = uuid.uuid4()
        self.current_player = self.white if self.current_player != self.white else self.black

        embed = discord.Embed(title="New Turn", description=f"It's {posessive(self.current_player.user.name)} turn.",
                              color=self.current_player.get_embed_color())

        embed.set_thumbnail(url=self.current_player.user.display_avatar.url)

        await self.thread.send(content=f"{self.current_player.user.mention}, it's your turn.", embed=embed)

        await self.turn_timer()

    async def end_current_turn(self):
        self.turn_uuid = None

        async with self.thread.typing():
            with chess.helpers.get_board_png(board=self.board) as board_png:
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

        await asyncio.sleep(120)
        if turn_uuid == self.turn_uuid and self.retrieve_game(self.thread.id):
            msg = f"{self.current_player.user.mention} took too long to move."
            embed = discord.Embed(title=f"{self.current_player.user.name} timed out.",
                                  description=msg, color=support.Color.red())
            await self.thread.send(embed=embed)

            await self.end_game(reason="timeout", player=self.current_player)

    async def end_game(self, reason: str, **kwargs):
        self.__all_games__.pop(self.thread.id)

        async def forfeit():
            forfeiter: ChessPlayer = kwargs.get("player")

            await self.thread.edit(name=f"{self.thread.name} - Game Over!")

            if self.has_started:
                winner = forfeiter.opponent

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
            offender: ChessPlayer = kwargs.get("player")

            msg = f"You took too long to move in your chess match against {offender.opponent.user.mention} in " \
                  f"{self.guild}. I have forfeited the match on your behalf, and {offender.opponent.user.name} has " \
                  f"won on time."
            embed = discord.Embed(title="You timed out.", description=msg, color=support.Color.red(),
                                  timestamp=discord.utils.utcnow())
            await offender.user.send(embed=embed)

            await self.thread.edit(name=f"{self.thread.name} - Game Over!")

            msg = f"{offender.opponent.user.mention} wins on time.\n" \
                  f"\n" \
                  f"This thread will be automatically deleted in 60 seconds.\n" \
                  f"\n" \
                  f"Thanks for playing!"

            embed = discord.Embed(title=f"Chess: Game Over! {offender.opponent.user.name} wins!",
                                  description=msg, color=support.Color.mint())

            timeout_msg = await self.thread.send(embed=embed)
            await timeout_msg.pin()

        async def stalemate():
            msg = "The match ended in a stalemate.\n" \
                  "" \
                  "This thread will be automatically deleted in 60 seconds.\n" \
                  "\n" \
                  "Thanks for playing!"

            embed = discord.Embed(title="Chess: Game Over! It's a draw!", description=msg, color=support.Color.mint())

            stalemate_msg = await self.thread.send(embed=embed)
            await stalemate_msg.pin()

        async def checkmate():
            winner = kwargs.get("winner")

            msg = f"{winner.user.mention} wins by checkmate. Congratulations!\n" \
                  f"\n" \
                  f"This thread will be automatically deleted in 60 seconds.\n" \
                  f"\n" \
                  f"Thanks for playing!"

            embed = discord.Embed(title=f"Chess: Game Over! {winner.user.name} wins!",
                                  description=msg,
                                  color=support.Color.mint())

            checkmate_msg = await self.thread.send(embed=embed)
            await checkmate_msg.pin()

        reason_map = {
            "forfeit": forfeit,
            "draw": draw,
            "timeout": timeout,
            "stalemate": stalemate,
            "checkmate": checkmate,
        }

        await reason_map[reason]()

        await asyncio.sleep(60)
        await self.thread.delete()


class ChessPlayer:
    def __init__(self, user: discord.User, game: ChessGame):
        self.user = user
        self.game = game

        self.is_ready = False
        self.opponent = None
        self.has_proposed_draw = False
        self.color: pychess.Color = None
        self.piece_symbols: list[str] = None

    async def ready(self):
        self.is_ready = True

        embed = discord.Embed(title=f"{self.user.name} is ready!",
                              description=f"{self.user.mention} is ready to play.",
                              color=support.Color.mint())

        await self.game.thread.send(embed=embed)

        await self.game.check_ready_players()

    async def move(self, ctx: discord.ApplicationContext):
        view = chess.ChessMoveView(ctx=ctx, player=self)
        move = await view.initiate_selection()

        processor = ChessEventProcessor(self.game)
        processor.move_event(player=self, move=move, move_data=view.move_data)

        if move.promotion:
            processor.promotion_event(self, view.move_data)

        board_copy = self.game.board.copy(stack=1)
        board_copy.pop()

        if board_copy.is_castling(move):
            processor.castle_event(self)
        if board_copy.is_capture(move):
            processor.capture_event(self)

        if self.game.board.is_checkmate():
            processor.checkmate_event(self.opponent)
        elif self.game.board.is_stalemate():
            processor.stalemate_event()
        elif self.game.board.is_check():
            processor.check_event(self.opponent)

        await self.end_turn()

    async def view_board(self, ctx: discord.ApplicationContext):
        view = chess.ChessBoardView(ctx=ctx, player=self)
        await view.initiate_view()

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

    async def end_turn(self):
        await self.game.end_current_turn()

    def populate_color_based_metadate(self):
        self.color = pychess.WHITE if self == self.game.white else pychess.BLACK
        self.opponent = self.game.black if self.color == pychess.WHITE else self.game.white

    def get_embed_color(self):
        embed_colors = {
            pychess.WHITE: support.Color.white(),
            pychess.BLACK: support.Color.black(),
        }

        return embed_colors[self.color]

    def __str__(self):
        return self.user.name


class ChessEventProcessor:
    def __init__(self, game: ChessGame):
        self.game = game

    def move_event(self, player: ChessPlayer, move: pychess.Move, move_data: dict):
        self.game.board.push(move)
        self.game.move_history.append(self.game.board.copy(stack=1))

        piece_type: str = move_data["piece_type"]
        origin: str = square_name(move_data["origin"])
        destination: str = square_name(move_data["destination"])

        msg = f"**{player.user.mention}** moves **{piece_type.capitalize()}** from {origin.capitalize()} " \
              f"to {destination.capitalize()}."

        embed = discord.Embed(title="Piece Moved", description=msg, color=player.get_embed_color())

        self.game.turn_record = embed

    def promotion_event(self, player: ChessPlayer, move_data: dict):
        piece_type: str = move_data["piece_type"]
        destination: str = move_data["destination"]
        promotion: str = move_data["promotion"]

        msg = f"**{player.user.name}** promotes " \
              f"**{piece_type.capitalize()} ({square_name(destination).capitalize()})** " \
              f"to a {chess.helpers.convert_piece_format(promotion, 'name').capitalize()}."

        self.game.turn_record.add_field(name="Pawn Promoted", value=msg, inline=False)

    def castle_event(self, player: ChessPlayer):
        msg = f"**{player.user.name}** castles."

        self.game.turn_record.add_field(name="Castle Performed", value=msg, inline=False)

    def capture_event(self, player: ChessPlayer):
        board_copy = self.game.board.copy()
        move = board_copy.pop()

        square = discord.utils.find(
            lambda sq:
            board_copy.piece_at(sq) and
            (board_copy.piece_at(sq).piece_type == pychess.PAWN or not board_copy.is_en_passant(move)) and
            board_copy.color_at(sq) is not player.color,

            [move.to_square, move.to_square - 8, move.to_square + 8]
        )

        captured_piece = chess.helpers.convert_piece_format(board_copy.piece_at(square), "name")

        msg = f"**{player.user.name}** captures {player.opponent.user.mention}'s **{captured_piece.capitalize()} " \
              f"({square_name(move.to_square).capitalize()})**"

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
