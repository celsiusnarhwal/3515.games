########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import math
import re
from collections import deque
from io import StringIO
from tempfile import TemporaryDirectory

import discord
from discord import ButtonStyle, Interaction
from discord.ui import Button, InputText, Modal, Select
from discord.ui import button as discord_button
from path import Path

import chess as pychess
import chess.pgn as pychess_pgn
import database.models as orm
import support
from chess import square_name
from cogs import chess
from support import View


class ChessSelect(Select):
    def __init__(self, stage: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage = stage
        self.embed: discord.Embed = None

    def add_option(self, **kwargs):
        if not any(option.value == kwargs.get("value") for option in self.options):
            super().add_option(**kwargs)


# Contrary to popular belief, stupid things that work are, in fact, still stupid.
class ChessMoveView(View):
    """
    Provides a user interface for a player to move a piece.
    """

    # Stages
    # 0: Select piece type
    # 1: Select piece (if multiple)
    # 2: Select destination square
    # 3: Select promotion piece (if applicable)
    # 4: Confirm move

    PIECE_SELECTION, ORIGIN, DESTINATION, PROMOTION, CONFIRMATION = range(5)

    def __init__(self, player: chess.ChessPlayer, **kwargs):
        super().__init__(**kwargs)
        self.player = player
        self.uuid = player.game.turn_uuid

        self.move_data = chess.ChessMoveData()

        self.board = self.player.game.board
        self.legal_moves = dict()

        self.image_data = {
            "board": self.board,
            "orientation": self.player.color,
            "fill": dict(),
            "lastmove": None,
            "squares": None,
            "arrows": [],
        }

        self.current_stage = self.PIECE_SELECTION
        self.stage_history = []

        self.stages = [
            ChessSelect(
                placeholder="Select a piece",
                min_values=1,
                max_values=1,
                stage=self.PIECE_SELECTION,
            ),
            ChessSelect(
                placeholder="Select a piece",
                min_values=1,
                max_values=1,
                stage=self.ORIGIN,
            ),
            ChessSelect(
                placeholder="Select a square",
                min_values=1,
                max_values=1,
                stage=self.DESTINATION,
            ),
            ChessSelect(
                placeholder="Select a promotion",
                min_values=1,
                max_values=1,
                stage=self.PROMOTION,
            ),
        ]

        for move in self.board.legal_moves:
            if self.legal_moves.get(move.from_square):
                self.legal_moves[move.from_square].append(move.to_square)
            else:
                self.legal_moves[move.from_square] = [move.to_square]

        for menu in self.stages:
            menu.callback = self.select_menu_callback

    async def interaction_check(self, interaction: Interaction) -> bool:
        if not chess.ChessGame.retrieve_game(self.player.game.thread.id):
            for child in self.children:
                child.disabled = True
                await interaction.response.edit_message(view=self)
        elif self.uuid != self.player.game.turn_uuid:
            msg = "Looks like this message is outdated. You'll have to use `/chess move` again to make a move."
            embed = discord.Embed(
                title="Whoops.", description=msg, color=support.Color.error()
            )

            await interaction.response.edit_message(
                embed=embed, view=None, attachments=[]
            )
        else:
            return super().interaction_check(interaction)

    async def select_menu_callback(self, interaction: Interaction):
        menu: ChessSelect = discord.utils.find(
            lambda x: isinstance(x, ChessSelect) and x.stage == self.current_stage,
            self.children,
        )

        for option in menu.options:
            option.default = False

        chosen_option = discord.utils.find(
            lambda x: x.value == menu.values[0], menu.options
        )
        chosen_option.default = True

        next_button = discord.utils.find(
            lambda b: isinstance(b, Button) and b.label == "Next", self.children
        )
        next_button.disabled = False

        await interaction.response.edit_message(view=self)

    async def back_button_callback(self, interaction: Interaction):
        move_data_keys = {
            self.PIECE_SELECTION: "piece",
            self.ORIGIN: "origin",
            self.DESTINATION: "destination",
            self.PROMOTION: "promotion",
        }

        reset_values = {
            self.PIECE_SELECTION: None,
            self.ORIGIN: 0,
            self.DESTINATION: 0,
            self.PROMOTION: None,
        }

        if self.current_stage in move_data_keys.keys():
            self.move_data[move_data_keys[self.current_stage]] = reset_values[
                self.current_stage
            ]
            self.stages[self.current_stage].options.clear()
            self.stages[self.current_stage].values.clear()

        self.current_stage = self.stage_history.pop()

        self.reset_image_data()

        await self.present(interaction=interaction)

    async def next_button_callback(self, interaction: Interaction):
        def determine_next_stage():
            def from_piece_selection():
                origin_squares = [
                    square
                    for square in self.legal_moves.keys()
                    if self.board.piece_at(square).piece_type
                    == self.move_data["piece"].piece_type
                ]

                if len(origin_squares) > 1:
                    return self.ORIGIN
                else:
                    self.move_data["origin"] = origin_squares[0]
                    return from_origin()

            def from_origin():
                if len(self.legal_moves[self.move_data["origin"]]) > 1:
                    return self.DESTINATION
                else:
                    self.move_data["destination"] = self.legal_moves[
                        self.move_data["origin"]
                    ][0]
                    return from_destination()

            def from_destination():
                origin = self.move_data["origin"]
                destination = self.move_data["destination"]

                try:
                    self.board.find_move(origin, destination, promotion=pychess.QUEEN)
                except ValueError:
                    return self.CONFIRMATION
                else:
                    return self.PROMOTION

            stages = {
                self.PIECE_SELECTION: from_piece_selection,
                self.ORIGIN: from_origin,
                self.DESTINATION: from_destination,
            }

            try:
                return stages[self.current_stage]()
            except KeyError:
                return self.current_stage + 1

        move_data_keys = {
            self.PIECE_SELECTION: "piece",
            self.ORIGIN: "origin",
            self.DESTINATION: "destination",
            self.PROMOTION: "promotion",
        }

        self.move_data[move_data_keys[self.current_stage]] = self.stages[
            self.current_stage
        ].values[0]

        move_data_values = {
            self.PIECE_SELECTION: chess.ChessPiece.from_symbol(self.move_data["piece"]),
            self.ORIGIN: int(self.move_data["origin"]),
            self.DESTINATION: int(self.move_data["destination"]),
            self.PROMOTION: chess.ChessPiece.from_symbol(self.move_data["promotion"]),
        }

        self.move_data[move_data_keys[self.current_stage]] = move_data_values[
            self.current_stage
        ]

        self.stage_history.append(self.current_stage)

        self.current_stage = determine_next_stage()

        self.reset_image_data()

        await self.present(interaction=interaction)

    async def confirm_button_callback(self, interaction: Interaction):
        self.success = True
        await interaction.response.edit_message(
            content="Making move...", embed=None, view=None, attachments=[]
        )

        self.stop()

    def configure_buttons(self):
        if self.stage_history:
            back_button = Button(label="Back", style=ButtonStyle.red)
            back_button.callback = self.back_button_callback
            self.add_item(back_button)

        if self.current_stage != self.CONFIRMATION:
            next_button = Button(
                label="Next",
                style=ButtonStyle.grey,
                disabled=not any(
                    option.default for option in self.stages[self.current_stage].options
                ),
            )
            next_button.callback = self.next_button_callback
            self.add_item(next_button)

        if self.current_stage == self.CONFIRMATION:
            confirm_button = Button(label="Confirm", style=ButtonStyle.green)
            confirm_button.callback = self.confirm_button_callback
            self.add_item(confirm_button)

    def get_move(self):
        return pychess.Move(
            from_square=self.move_data["origin"],
            to_square=self.move_data["destination"],
            promotion=self.move_data["promotion"] or None,
        )

    def reset_image_data(self):
        self.image_data = {
            "board": self.board,
            "orientation": self.player.color,
            "fill": dict(),
            "lastmove": None,
            "squares": None,
            "arrows": [],
        }

    async def present(self, interaction: Interaction = None):
        async def piece_selection():
            menu = self.stages[self.PIECE_SELECTION]

            for square in self.legal_moves.keys():
                piece = self.board.piece_at(square)

                menu.add_option(
                    label=piece.name().capitalize(),
                    value=piece.symbol(),
                )

            msg = (
                "Select a piece from the dropdown menu below. Only pieces you can move on this turn "
                "are displayed."
            )
            menu.embed = discord.Embed(
                title="Piece Selection", description=msg, color=support.Color.mint()
            )

            return menu

        async def origin():
            menu = self.stages[self.ORIGIN]
            selected_piece = self.move_data["piece"]

            for square in self.legal_moves.keys():
                if self.board.piece_at(square) == selected_piece:
                    menu.add_option(
                        label=f"{selected_piece.name().capitalize()} ({square_name(square).capitalize()})",
                        value=str(square),
                    )

                    self.image_data["fill"][square] = "#ced179"

            menu.options.sort(
                key=lambda option: [
                    "abcdefgh12345678".index(char)
                    for char in square_name(int(option.value))
                ]
            )

            msg = (
                f"Select a **{selected_piece}** to move. "
                f"Only **{selected_piece}s** you can move on this turn are displayed."
            )

            menu.embed = discord.Embed(
                title="Piece Selection", description=msg, color=support.Color.mint()
            )

            return menu

        async def destination():
            menu = self.stages[self.DESTINATION]
            orig = self.move_data["origin"]

            for dest in self.legal_moves[orig]:
                menu.add_option(
                    label=f"{square_name(dest).capitalize()}",
                    value=str(dest),
                )

            menu.options.sort(
                key=lambda option: [
                    "abcdefgh12345678".index(char)
                    for char in square_name(int(option.value))
                ]
            )

            selected_piece = self.move_data["piece"]
            msg = (
                f"Select a square to move **{selected_piece} "
                f"({square_name(orig).capitalize()})** "
                f"to. Only legal destinations are displayed."
            )

            menu.embed = discord.Embed(
                title="Destination Square", description=msg, color=support.Color.mint()
            )

            self.image_data["squares"] = pychess.SquareSet(
                [square for square in self.legal_moves[orig]]
            )
            self.image_data["fill"].clear()
            self.image_data["fill"][self.move_data["origin"]] = "#ced179"

            return menu

        async def promotion():
            menu = self.stages[self.PROMOTION]

            for piece_symbol in pychess.PIECE_SYMBOLS:
                if piece_symbol != "p":
                    menu.add_option(
                        label=chess.ChessPiece.from_symbol(piece_symbol)
                        .name()
                        .capitalize(),
                        value=piece_symbol,
                    )

            selected_piece = self.move_data["piece"]
            orig = self.move_data["origin"]

            msg = (
                f"**{selected_piece} "
                f"({square_name(orig).capitalize()})** "
                f"will reach its last rank and must be promoted. Choose a piece to promote it to."
            )

            menu.embed = discord.Embed(
                title="Pawn Promotion", description=msg, color=support.Color.mint()
            )

            self.image_data["fill"].clear()
            self.image_data["lastmove"] = self.get_move()
            self.image_data["arrows"] = [
                (self.move_data["origin"], self.move_data["destination"])
            ]

            return menu

        if self.current_stage != self.CONFIRMATION:
            stages = {
                self.PIECE_SELECTION: piece_selection,
                self.ORIGIN: origin,
                self.DESTINATION: destination,
                self.PROMOTION: promotion,
            }

            self.clear_items()

            select_menu = await stages[self.current_stage]()
            async with chess.get_board_image(**self.image_data) as board_png:
                select_menu.embed.set_image(url=f"attachment://{board_png.filename}")
                self.add_item(select_menu)

                self.configure_buttons()

                if interaction:
                    await interaction.response.defer()
                    await interaction.edit_original_response(
                        embed=select_menu.embed,
                        file=board_png,
                        attachments=[],
                        view=self,
                    )
                else:
                    await self.ctx.defer(ephemeral=True)
                    await self.ctx.respond(
                        embed=select_menu.embed,
                        file=board_png,
                        view=self,
                        ephemeral=True,
                    )
        else:
            piece = self.move_data["piece"]
            origin_square = self.move_data["origin"]
            destination_square = self.move_data["destination"]

            move_str = (
                f"- Move **{piece} ({square_name(origin_square).capitalize()})** to "
                f"**{square_name(destination_square).capitalize()}**"
            )

            if self.move_data["promotion"]:
                promotion_piece = self.move_data["promotion"]
                move_str += (
                    f"\n- Promote aforementioned {piece} to " f"**{promotion_piece}**"
                )

            self.clear_items()
            self.configure_buttons()

            msg = "Please confirm the following move:\n\n" + move_str

            embed = discord.Embed(
                title="Confirm Move", description=msg, color=support.Color.mint()
            )

            self.image_data["fill"].clear()
            self.image_data["lastmove"] = self.get_move()
            self.image_data["arrows"] = [(origin_square, destination_square)]

            async with chess.get_board_image(**self.image_data) as board_png:
                embed.set_image(url=f"attachment://{board_png.filename}")
                await interaction.response.defer()
                await interaction.edit_original_response(
                    embed=embed, file=board_png, attachments=[], view=self
                )

    async def start(self):
        await self.present()
        await self.wait()

        return self.get_move()


class ChessBoardView(View):
    class MoveHistoryPaginator:
        def __init__(self, board: chess.ChessBoard):
            self.board = board
            self.page_number = len(board.move_stack)
            self.popped_moves = deque()

        def indicator(self):
            if self.page_number == 0:
                return "Match Start"

            color = "White" if not self.current().turn else "Black"
            return f"Turn {math.ceil(self.page_number / 2)} of {math.ceil(len(self) / 2)} ({color})"

        def current(self):
            return self.board

        def first(self):
            while self.board.move_stack:
                self.popped_moves.appendleft(self.board.pop())

            self.board.reset()
            self.page_number = 0

        def previous(self):
            self.popped_moves.appendleft(self.board.pop())
            self.page_number -= 1

        def next(self):
            self.board.push(self.popped_moves.popleft())
            self.page_number += 1

        def last(self):
            while self.popped_moves:
                self.board.push(self.popped_moves.popleft())

            self.page_number = len(self)

        def has_next(self):
            return len(self.popped_moves) > 0

        def has_previous(self):
            return self.page_number > 0

        def __len__(self):
            return len(self.board.move_stack) + len(self.popped_moves)

    def __init__(self, player: chess.ChessPlayer, **kwargs):
        super().__init__(**kwargs)
        self.player = player

        self.game = self.player.game
        self.history = self.MoveHistoryPaginator(self.game.board.copy())
        self.highlight_last_move = False

        self.image_data = {
            "board": self.game.board,
            "orientation": self.player.color,
            "arrows": [],
            "lastmove": None,
            "coordinates": True,
        }

    @discord_button(
        label="Flip Orientation", custom_id="orientation", style=ButtonStyle.gray, row=2
    )
    async def flip_orientation(self, _, interaction: Interaction):
        self.image_data["orientation"] = not self.image_data["orientation"]

        await self.present(interaction)

    @discord_button(
        label="Hide Coordinates", custom_id="coordinates", style=ButtonStyle.gray, row=2
    )
    async def toggle_coordinates(self, _, interaction: Interaction):
        self.image_data["coordinates"] = not self.image_data["coordinates"]

        button = discord.utils.find(
            lambda b: b.custom_id == "coordinates", self.children
        )
        button.label = (
            "Hide Coordinates" if self.image_data["coordinates"] else "Show Coordinates"
        )

        await self.present(interaction)

    async def toggle_move_highlight(self, interaction: Interaction):
        self.highlight_last_move = not self.highlight_last_move

        board = self.history.current()
        move = board.peek()

        if self.highlight_last_move:
            self.image_data["lastmove"] = move
            self.image_data["arrows"] = [(move.from_square, move.to_square)]
        else:
            self.image_data["lastmove"] = None
            self.image_data["arrows"] = []

        button = discord.utils.find(lambda b: b.custom_id == "last_move", self.children)
        button.label = (
            button.label.replace("Highlight", "Unhighlight")
            if self.image_data["lastmove"]
            else button.label.replace("Unhighlight", "Highlight")
        )

        await self.present(interaction)

    async def toggle_move_history(self, interaction: Interaction):
        move_history_button: Button = discord.utils.find(
            lambda b: b.custom_id == "move_history", self.children
        )
        last_move_button = discord.utils.find(
            lambda b: b.custom_id == "last_move", self.children
        )

        if move_history_button.label == "Show Move History":
            move_history_button.label = "Hide Move History"
            last_move_button.label = last_move_button.label.replace("Last ", "")

            first_button = Button(
                label="",
                emoji="⏮",
                style=ButtonStyle.gray,
                custom_id="history_first",
                row=1,
                disabled=not self.history.has_previous(),
            )
            first_button.callback = self.history_first
            self.add_item(first_button)

            previous_button = Button(
                label="",
                emoji="⏪",
                style=ButtonStyle.gray,
                custom_id="history_previous",
                row=1,
                disabled=not self.history.has_previous(),
            )
            previous_button.callback = self.history_previous
            self.add_item(previous_button)

            indicator_button = Button(
                label=self.history.indicator(),
                style=ButtonStyle.gray,
                custom_id="history_indicator",
                disabled=True,
                row=1,
            )
            self.add_item(indicator_button)

            next_button = Button(
                label="",
                emoji="⏩",
                style=ButtonStyle.gray,
                custom_id="history_next",
                row=1,
                disabled=not self.history.has_next(),
            )
            next_button.callback = self.history_next
            self.add_item(next_button)

            last_button = Button(
                label="",
                emoji="⏭",
                style=ButtonStyle.gray,
                custom_id="history_last",
                row=1,
                disabled=not self.history.has_next(),
            )
            last_button.callback = self.history_last
            self.add_item(last_button)

            await self.present(interaction)

        elif move_history_button.label == "Hide Move History":
            move_history_button.label = "Show Move History"
            last_move_button.label = last_move_button.label.replace("Move", "Last Move")

            self.history.last()
            self.refresh_page()

            button_ids = [
                "history_first",
                "history_previous",
                "history_indicator",
                "history_next",
                "history_last",
            ]
            for button_id in button_ids:
                button = discord.utils.find(
                    lambda b: b.custom_id == button_id, self.children
                )
                self.remove_item(button)

        await self.present(interaction)

    async def history_first(self, interaction: Interaction):
        self.history.first()
        self.refresh_page()
        await self.present(interaction)

    async def history_previous(self, interaction: Interaction):
        self.history.previous()
        self.refresh_page()
        await self.present(interaction)

    async def history_next(self, interaction: Interaction):
        self.history.next()
        self.refresh_page()
        await self.present(interaction)

    async def history_last(self, interaction: Interaction):
        self.history.last()
        self.refresh_page()
        await self.present(interaction)

    def refresh_page(self):
        board = self.history.current()

        self.image_data["board"] = board

        last_move_button = discord.utils.find(
            lambda b: b.custom_id == "last_move", self.children
        )

        try:
            move = board.peek()
        except IndexError:
            last_move_button.disabled = True
            self.image_data["lastmove"] = None
            self.image_data["arrows"] = []
        else:
            last_move_button.disabled = False
            if self.highlight_last_move:
                self.image_data["lastmove"] = move
                self.image_data["arrows"] = [(move.from_square, move.to_square)]
            else:
                self.image_data["lastmove"] = None
                self.image_data["arrows"] = []

        indicator_button = discord.utils.find(
            lambda b: b.custom_id == "history_indicator", self.children
        )
        indicator_button.label = self.history.indicator()

        first_button = discord.utils.find(
            lambda b: b.custom_id == "history_first", self.children
        )
        previous_button = discord.utils.find(
            lambda b: b.custom_id == "history_previous", self.children
        )
        first_button.disabled = (
            previous_button.disabled
        ) = not self.history.has_previous()

        next_button = discord.utils.find(
            lambda b: b.custom_id == "history_next", self.children
        )
        last_button = discord.utils.find(
            lambda b: b.custom_id == "history_last", self.children
        )
        next_button.disabled = last_button.disabled = not self.history.has_next()

    async def present(self, interaction: Interaction = None):
        async with chess.get_board_image(**self.image_data) as board_png:
            if interaction:
                await interaction.response.defer()
                await interaction.edit_original_response(
                    file=board_png, attachments=[], view=self
                )
            else:
                await self.ctx.defer(ephemeral=True)
                await self.ctx.respond(file=board_png, view=self, ephemeral=True)

    async def initiate_view(self):
        if len(self.history) > 0:
            last_move_button = Button(
                label="Highlight Last Move",
                custom_id="last_move",
                style=ButtonStyle.gray,
                row=3,
            )
            last_move_button.callback = self.toggle_move_highlight
            self.add_item(last_move_button)

            move_history_button = Button(
                label="Show Move History",
                custom_id="move_history",
                style=ButtonStyle.gray,
                row=3,
            )
            move_history_button.callback = self.toggle_move_history
            self.add_item(move_history_button)

        await self.present()


class ChessEndgameView(View):
    def __init__(self, game: chess.ChessGame):
        super().__init__()
        self.game = game
        self.has_saved = []

    async def interaction_check(self, interaction: Interaction) -> bool:
        player: chess.ChessPlayer = self.game.retrieve_player(interaction.user)
        if not player:
            msg = "Only users who played in this game can save it to their history."
            embed = discord.Embed(
                title="You didn't play in this game.",
                description=msg,
                color=support.Color.error(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        elif interaction.user in self.has_saved:
            msg = "You've already saved this game. You can't save it again."
            embed = discord.Embed(
                title="You did that already.",
                description=msg,
                color=support.Color.error(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            return await super().interaction_check(interaction)

    @discord_button(label="Save Game", style=ButtonStyle.gray)
    async def save_game(self, _, interaction: Interaction):
        pgn = pychess_pgn.Game.from_board(self.game.board)

        headers = {
            "Event": f"{self.game.white.user.name} vs. {self.game.black.user.name}",
            "Site": self.game.guild.name,
            "Date": self.game.thread.created_at.strftime("%Y.%m.%d"),
            "White": f"{self.game.white.user.name}#{self.game.white.user.discriminator}",
            "Black": f"{self.game.black.user.name}#{self.game.black.user.discriminator}",
        }

        for header, content in headers.items():
            pgn.headers[header] = content

        match self.game.board.result():
            case "1-0":
                result = f"{self.game.white.user.name} wins"
            case "0-1":
                result = f"{self.game.black.user.name} wins"
            case _:
                result = "Draw"

        with orm.db_session:
            saved_games = orm.ChessGame.get_user_games(interaction.user)
            if saved_games.count() >= 25:
                saved_games.first().delete()

            orm.ChessGame(
                user_id=str(interaction.user.id),
                white=self.game.white.user.name,
                white_id=str(self.game.white.id),
                black=self.game.black.user.name,
                black_id=str(self.game.black.id),
                server=self.game.guild.name,
                result=result,
                date=self.game.thread.created_at,
                pgn=pgn.accept(chess.pychess_pgn.StringExporter()).replace(
                    '\n[Round "?"]\n', ""
                ),
            )

        self.has_saved.append(interaction.user)

        await interaction.response.send_message(
            "Game saved! Revisit it with `/chess replay`.", ephemeral=True
        )


class ChessReplayMenuView(View):
    async def select_menu_callback(self, interaction: Interaction):
        menu: Select = discord.utils.find(
            lambda x: isinstance(x, Select), self.children
        )

        for option in menu.options:
            option.default = False

        chosen_option = discord.utils.find(
            lambda x: x.value == menu.values[0], menu.options
        )
        chosen_option.default = True

        for button in [child for child in self.children if isinstance(child, Button)]:
            button.disabled = False

        with orm.db_session:
            game: orm.ChessGame = orm.ChessGame.get(id=int(menu.values[0]))

        embed = (
            discord.Embed(
                title=f"{game.white} vs. {game.black}", color=support.Color.mint()
            )
            .add_field(name="Date", value=game.date.strftime("%Y-%m-%d"), inline=False)
            .add_field(name="Server", value=game.server, inline=False)
            .add_field(
                name="White", value=f"{game.white} (<@{game.white_id}>)", inline=False
            )
            .add_field(
                name="Black", value=f"{game.black} (<@{game.black_id}>)", inline=False
            )
            .add_field(name="Result", value=game.result, inline=False)
        )

        await interaction.response.edit_message(embed=embed, view=self)

    @orm.db_session
    def get_menu(self) -> Select:
        menu = Select(
            min_values=1,
            max_values=1,
            placeholder="Select a game",
            custom_id="game_menu",
            row=1,
        )

        menu.callback = self.select_menu_callback

        for game in orm.ChessGame.get_user_games(self.ctx.user):
            menu.add_option(
                label=f"{game.white} vs. {game.black}",
                description=f"{game.server} / {game.date.strftime('%Y.%m.%d')}",
                value=str(game.id),
            )

        return menu

    @discord_button(
        label="Replay Game",
        style=ButtonStyle.gray,
        custom_id="replay",
        disabled=True,
        row=2,
    )
    async def replay_game(self, _, interaction: Interaction):
        select_menu: Select = discord.utils.find(
            lambda x: isinstance(x, Select), self.children
        )
        game_id = int(select_menu.values[0])

        with orm.db_session:
            game = orm.ChessGame.get(id=game_id)

        view = ChessReplayView(game.pgn)
        await view.initiate_view(interaction)

    @discord_button(
        label="Export PGN",
        style=ButtonStyle.gray,
        custom_id="export",
        disabled=True,
        row=2,
    )
    async def export_game(self, _, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)

        select_menu: Select = discord.utils.find(
            lambda x: isinstance(x, Select), self.children
        )
        game_id = int(select_menu.values[0])

        with orm.db_session:
            game = orm.ChessGame.get(id=game_id)

        with TemporaryDirectory() as tmp, Path(tmp):
            filename = (
                f"({game.server}) {game.white} vs. {game.black} [{game.date}].pgn"
            )
            open(filename, "w+").write(game.pgn)
            pgn_file = discord.File(filename)
            await interaction.followup.send(
                content="Your PGN is ready!", file=pgn_file, ephemeral=True
            )

    @discord_button(
        label="Import PGN",
        style=ButtonStyle.gray,
        custom_id="import",
        disabled=False,
        row=2,
    )
    async def import_game(self, _, interaction: Interaction):
        class PGNImportModal(Modal):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

                self.add_item(
                    InputText(
                        label="PGN",
                        custom_id="pgn_input",
                        min_length=1,
                        max_length=4000,
                        value="",
                        placeholder="PGNs must be 4000 characters or fewer. Discord limitation, sorry!",
                        style=discord.InputTextStyle.multiline,
                    )
                )

            async def callback(self, interaction: Interaction):
                pgn = re.sub("\n{2,}", "\n", self.children[0].value)
                view = ChessReplayView(pgn)
                await view.initiate_view(interaction)

        modal = PGNImportModal(title="Import PGN", custom_id="import_modal")

        await interaction.response.send_modal(modal)

    @discord_button(
        label="Delete Game",
        style=ButtonStyle.red,
        custom_id="delete",
        disabled=True,
        row=3,
    )
    async def delete_game(self, _, interaction: Interaction):
        select_menu: Select = discord.utils.find(
            lambda x: isinstance(x, Select), self.children
        )
        game_id = int(select_menu.values[0])

        with orm.db_session:
            orm.ChessGame[game_id].delete()

        self.remove_item(select_menu)
        self.add_item(self.get_menu())

        replay_button = discord.utils.find(
            lambda b: isinstance(b, Button) and b.custom_id == "replay", self.children
        )
        delete_button = discord.utils.find(
            lambda b: isinstance(b, Button) and b.custom_id == "delete", self.children
        )
        replay_button.disabled = delete_button.disabled = True

        with orm.db_session:
            if orm.ChessGame.get_user_games(self.ctx.user):
                await interaction.response.edit_message(view=self)
                await interaction.followup.send("Game deleted!", ephemeral=True)
            else:
                await interaction.response.edit_message(
                    content="All games deleted!", embed=None, view=None
                )

    @discord_button(
        label="Delete All Games",
        style=ButtonStyle.red,
        custom_id="delete_all",
        disabled=False,
        row=3,
    )
    async def delete_all_games(self, _, interaction: Interaction):
        with orm.db_session:
            orm.ChessGame.select(
                lambda g: g.user_id == str(interaction.user.id)
            ).delete(bulk=True)

        await interaction.response.edit_message(
            content="All games deleted!", embed=None, view=None
        )

    async def initiate_view(self):
        with orm.db_session:
            if not orm.ChessGame.get_user_games(self.ctx.user):
                msg = "You haven't saved any games. Save a game or two, then check back here."
                embed = discord.Embed(
                    title="Nothing to see here.",
                    description=msg,
                    color=support.Color.error(),
                )
                await self.ctx.respond(embed=embed, ephemeral=True)
            else:
                menu = self.get_menu()
                self.add_item(menu)

                msg = (
                    "Select a game from the menu below. You can save up to 25 games at a time.\n"
                    "\n"
                    "Alternatively, you can import your own PGN using the Import PGN button - even if "
                    "you played the game somewhere else."
                )

                embed = discord.Embed(
                    title="Saved Chess Games",
                    description=msg,
                    color=support.Color.mint(),
                )

                await self.ctx.respond(embed=embed, view=self, ephemeral=True)


# believe it or not, subclassing ChessBoardView actually makes things worse!
class ChessReplayView(View):
    class MoveHistoryPaginator:
        def __init__(self, board: pychess.Board):
            self.board = board
            self.page_number = 0
            self.popped_moves = deque()

        def indicator(self):
            if self.page_number == 0:
                return "Match Start"

            color = "White" if not self.current().turn else "Black"
            return f"Turn {math.ceil(self.page_number / 2)} of {math.ceil(len(self) / 2)} ({color})"

        def current(self):
            return self.board

        def first(self):
            while self.board.move_stack:
                self.popped_moves.appendleft(self.board.pop())

            self.board.reset()
            self.page_number = 0

        def previous(self):
            self.popped_moves.appendleft(self.board.pop())
            self.page_number -= 1

        def next(self):
            self.board.push(self.popped_moves.popleft())
            self.page_number += 1

        def last(self):
            while self.popped_moves:
                self.board.push(self.popped_moves.popleft())

            self.page_number = len(self)

        def has_next(self):
            return len(self.popped_moves) > 0

        def has_previous(self):
            return self.page_number > 0

        def __len__(self):
            return len(self.board.move_stack) + len(self.popped_moves)

    def __init__(self, pgn: str, **kwargs):
        super().__init__(**kwargs)
        board = pychess_pgn.read_game(StringIO(pgn), Visitor=pychess_pgn.BoardBuilder)
        self.history = self.MoveHistoryPaginator(board)
        self.highlight_last_move = False
        self.show_analysis = False

        self.image_data = {
            "board": self.history.current(),
            "orientation": True,
            "arrows": [],
            "lastmove": None,
            "coordinates": True,
        }

    @discord_button(
        label="Flip Orientation", custom_id="orientation", style=ButtonStyle.gray, row=2
    )
    async def flip_orientation(self, _, interaction: Interaction):
        self.image_data["orientation"] = not self.image_data["orientation"]

        await self.present(interaction)

    @discord_button(
        label="Hide Coordinates", custom_id="coordinates", style=ButtonStyle.gray, row=2
    )
    async def toggle_coordinates(self, _, interaction: Interaction):
        self.image_data["coordinates"] = not self.image_data["coordinates"]

        button = discord.utils.find(
            lambda b: b.custom_id == "coordinates", self.children
        )
        button.label = (
            "Hide Coordinates" if self.image_data["coordinates"] else "Show Coordinates"
        )

        await self.present(interaction)

    @discord_button(
        label="Highlight Move",
        custom_id="last_move",
        style=ButtonStyle.gray,
        row=2,
        disabled=True,
    )
    async def toggle_move_highlight(self, _, interaction: Interaction):
        self.highlight_last_move = not self.highlight_last_move

        board = self.history.current()
        move = board.peek()

        if self.highlight_last_move:
            self.image_data["lastmove"] = move
            self.image_data["arrows"] = [(move.from_square, move.to_square)]
        else:
            self.image_data["lastmove"] = None
            self.image_data["arrows"] = []

        button = discord.utils.find(lambda b: b.custom_id == "last_move", self.children)
        button.label = (
            button.label.replace("Highlight", "Unhighlight")
            if self.image_data["lastmove"]
            else button.label.replace("Unhighlight", "Highlight")
        )

        await self.present(interaction)

    async def history_first(self, interaction: Interaction):
        self.history.first()
        self.refresh_page()
        await self.present(interaction)

    async def history_previous(self, interaction: Interaction):
        self.history.previous()
        self.refresh_page()
        await self.present(interaction)

    async def history_next(self, interaction: Interaction):
        self.history.next()
        self.refresh_page()
        await self.present(interaction)

    async def history_last(self, interaction: Interaction):
        self.history.last()
        self.refresh_page()
        await self.present(interaction)

    def refresh_page(self):
        board = self.history.current()

        self.image_data["board"] = board

        last_move_button = discord.utils.find(
            lambda b: b.custom_id == "last_move", self.children
        )

        try:
            move = board.peek()
        except IndexError:
            last_move_button.disabled = True
            self.image_data["lastmove"] = None
            self.image_data["arrows"] = []
        else:
            last_move_button.disabled = False
            if self.highlight_last_move:
                self.image_data["lastmove"] = move
                self.image_data["arrows"] = [(move.from_square, move.to_square)]
            else:
                self.image_data["lastmove"] = None
                self.image_data["arrows"] = []

        indicator_button = discord.utils.find(
            lambda b: b.custom_id == "history_indicator", self.children
        )
        indicator_button.label = self.history.indicator()

        first_button = discord.utils.find(
            lambda b: b.custom_id == "history_first", self.children
        )
        previous_button = discord.utils.find(
            lambda b: b.custom_id == "history_previous", self.children
        )
        first_button.disabled = (
            previous_button.disabled
        ) = not self.history.has_previous()

        next_button = discord.utils.find(
            lambda b: b.custom_id == "history_next", self.children
        )
        last_button = discord.utils.find(
            lambda b: b.custom_id == "history_last", self.children
        )
        next_button.disabled = last_button.disabled = not self.history.has_next()

    async def present(self, interaction):
        async with chess.get_board_image(**self.image_data) as board_png:
            await interaction.response.defer()
            await interaction.edit_original_response(
                file=board_png, attachments=[], view=self
            )

    async def initiate_view(self, interaction: Interaction):
        self.history.first()

        first_button = Button(
            label="",
            emoji="⏮",
            style=ButtonStyle.gray,
            custom_id="history_first",
            row=1,
            disabled=not self.history.has_previous(),
        )
        first_button.callback = self.history_first
        self.add_item(first_button)

        previous_button = Button(
            label="",
            emoji="⏪",
            style=ButtonStyle.gray,
            custom_id="history_previous",
            row=1,
            disabled=not self.history.has_previous(),
        )
        previous_button.callback = self.history_previous
        self.add_item(previous_button)

        indicator_button = Button(
            label=self.history.indicator(),
            style=ButtonStyle.gray,
            custom_id="history_indicator",
            disabled=True,
            row=1,
        )
        self.add_item(indicator_button)

        next_button = Button(
            label="",
            emoji="⏩",
            style=ButtonStyle.gray,
            custom_id="history_next",
            row=1,
            disabled=not self.history.has_next(),
        )
        next_button.callback = self.history_next
        self.add_item(next_button)

        last_button = Button(
            label="",
            emoji="⏭",
            style=ButtonStyle.gray,
            custom_id="history_last",
            row=1,
            disabled=not self.history.has_next(),
        )
        last_button.callback = self.history_last
        self.add_item(last_button)

        async with chess.get_board_image(**self.image_data) as board_png:
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send(
                file=board_png, embed=None, view=self, ephemeral=True
            )
