from __future__ import annotations

import chess as pychess
import discord
from chess import square_name
from discord import Interaction, ButtonStyle
from discord.ui import Select, Button, button as discord_button
from llist import dllist as DoublyLinkedList

import support
from cogs import chess
from support import EnhancedView


class ChessSelect(Select):
    def __init__(self, stage: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stage = stage
        self.embed: discord.Embed = None

    def add_option(self, **kwargs):
        if not any(option.value == kwargs.get("value") for option in self.options):
            super().add_option(**kwargs)


# who needs an interactive chess board, anyway?
class ChessMoveView(EnhancedView):
    """
    Provides a user interface for a player to move a piece.
    """
    # Stages
    # 0: Select piece type
    # 1: Select piece (if multiple)
    # 2: Select destination square
    # 3: Select promotion piece (if applicable)
    # 4: Confirm move

    [PIECE_SELECTION, ORIGIN, DESTINATION, PROMOTION, CONFIRMATION] = range(5)

    def __init__(self, player: chess.ChessPlayer, **kwargs):
        super().__init__(**kwargs)
        self.player = player

        self.move_data = {
            "piece_type": "",
            "origin": 0,
            "destination": 0,
            "promotion": "",
        }

        self.board = self.player.game.board
        self.player_legal_moves = dict()

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

        for move in self.board.legal_moves:
            if self.board.color_at(move.from_square) is player.color:
                if self.player_legal_moves.get(move.from_square):
                    self.player_legal_moves[move.from_square].append(move.to_square)
                else:
                    self.player_legal_moves[move.from_square] = [move.to_square]

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

        for menu in self.stages:
            menu.callback = self.select_menu_callback

    async def interaction_check(self, interaction: Interaction) -> bool:
        if chess.ChessGame.retrieve_game(self.player.game.thread.id):
            return super().interaction_check(interaction)
        else:
            for child in self.children:
                child.disabled = True
                await interaction.response.edit_message(view=self)

    async def select_menu_callback(self, interaction: Interaction):
        menu: ChessSelect = discord.utils.find(
            lambda x: isinstance(x, ChessSelect) and x.stage == self.current_stage, self.children
        )

        for option in menu.options:
            option.default = False

        chosen_option = discord.utils.find(lambda x: x.value == menu.values[0], menu.options)
        chosen_option.default = True

        next_button = discord.utils.find(lambda b: isinstance(b, Button) and b.label == "Next", self.children)
        next_button.disabled = False

        await interaction.response.edit_message(view=self)

    async def back_button_callback(self, interaction: Interaction):
        move_data_keys = {
            self.PIECE_SELECTION: "piece_type",
            self.ORIGIN: "origin",
            self.DESTINATION: "destination",
            self.PROMOTION: "promotion",
        }

        if self.current_stage in move_data_keys.keys():
            self.move_data[move_data_keys[self.current_stage]] = ""
            self.stages[self.current_stage].options.clear()
            self.stages[self.current_stage].values.clear()

        self.current_stage = self.stage_history.pop()

        self.reset_image_data()

        await self.present(interaction=interaction)

    async def next_button_callback(self, interaction: Interaction):
        def determine_next_stage():
            def from_piece_selection():
                squares = [square for square in self.player_legal_moves.keys() if
                           chess.helpers.convert_piece_format(self.board.piece_at(square), "name") == self.move_data[
                               "piece_type"]]

                if len(squares) > 1:
                    return self.ORIGIN
                else:
                    self.move_data["origin"] = squares[0]
                    return from_origin()

            def from_origin():
                if len(self.player_legal_moves[self.move_data["origin"]]) > 1:
                    return self.DESTINATION
                else:
                    self.move_data["destination"] = self.player_legal_moves[self.move_data["origin"]][0]
                    return from_destination()

            def from_destination():
                if self.move_data["piece_type"] == "pawn":
                    origin = self.move_data["origin"]
                    destination = self.move_data["destination"]

                    promotion = False
                    try:
                        # it doesn't actually matter what piece we check for here as long it's not a pawn. if a pawn
                        # can promote to one piece, it can promote to any of them.
                        self.board.find_move(origin, destination, promotion=6)
                    except ValueError:
                        pass
                    else:
                        promotion = True

                    if promotion:
                        return self.PROMOTION

                return self.CONFIRMATION

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
            self.PIECE_SELECTION: "piece_type",
            self.ORIGIN: "origin",
            self.DESTINATION: "destination",
            self.PROMOTION: "promotion",
        }

        try:
            self.move_data[move_data_keys[self.current_stage]] = int(self.stages[self.current_stage].values[0])
        except ValueError:
            self.move_data[move_data_keys[self.current_stage]] = self.stages[self.current_stage].values[0]

        self.stage_history.append(self.current_stage)

        self.current_stage = determine_next_stage()

        self.reset_image_data()

        await self.present(interaction=interaction)

    async def confirm_button_callback(self, interaction: Interaction):
        self.success = True
        await interaction.response.edit_message(content="Making move...", embed=None, view=None, attachments=[])

        self.stop()

    def configure_buttons(self):
        if self.current_stage > self.PIECE_SELECTION:
            back_button = Button(label="Back", style=ButtonStyle.red)
            back_button.callback = self.back_button_callback
            self.add_item(back_button)

        if self.current_stage != self.CONFIRMATION:
            next_button = Button(label="Next", style=ButtonStyle.grey,
                                 disabled=not any(option.default for option in self.stages[self.current_stage].options))
            next_button.callback = self.next_button_callback
            self.add_item(next_button)

        if self.current_stage == self.CONFIRMATION:
            confirm_button = Button(label="Confirm", style=ButtonStyle.green)
            confirm_button.callback = self.confirm_button_callback
            self.add_item(confirm_button)

    def get_move(self):
        return pychess.Move(from_square=self.move_data["origin"],
                            to_square=self.move_data["destination"],
                            promotion=self.move_data["promotion"] or None)

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

            for square in self.player_legal_moves.keys():
                symbol = self.board.piece_at(square).symbol()
                piece_name = chess.helpers.convert_piece_format(symbol, "name")

                menu.add_option(
                    label=piece_name.capitalize(),
                    value=piece_name
                )

            msg = "Select a piece from the dropdown menu below. Only pieces you can move on this turn " \
                  "are displayed."
            menu.embed = discord.Embed(title="Piece Selection", description=msg, color=support.Color.mint())

            return menu

        async def origin():
            menu = self.stages[self.ORIGIN]
            piece_name = self.move_data["piece_type"]

            for square in self.player_legal_moves.keys():
                if chess.helpers.convert_piece_format(self.board.piece_at(square), "name") == piece_name:
                    menu.add_option(
                        label=f"{piece_name.capitalize()} ({square_name(square).capitalize()})",
                        value=str(square)
                    )

                    self.image_data["fill"][square] = "#ced179"

            menu.options.sort(
                key=lambda option: ["abcdefgh12345678".index(char) for char in square_name(int(option.value))]
            )

            msg = f"Select a **{piece_name.capitalize()}** to move. Only **{piece_name.capitalize()}s** you can move " \
                  f"on this turn are displayed."

            menu.embed = discord.Embed(title="Piece Selection", description=msg, color=support.Color.mint())

            return menu

        async def destination():
            menu = self.stages[self.DESTINATION]
            orig = self.move_data["origin"]

            for dest in self.player_legal_moves[orig]:
                menu.add_option(
                    label=f"{square_name(dest).capitalize()}",
                    value=str(dest),
                )

            menu.options.sort(
                key=lambda option: ["abcdefgh12345678".index(char) for char in square_name(int(option.value))]
            )

            msg = f"Select a square to move **{self.move_data['piece_type'].capitalize()} " \
                  f"({square_name(orig).capitalize()})** " \
                  f"to. Only legal destinations are displayed."

            menu.embed = discord.Embed(title="Destination Square", description=msg, color=support.Color.mint())

            self.image_data["squares"] = pychess.SquareSet(
                [square for square in self.player_legal_moves[orig]]
            )
            self.image_data["fill"].clear()
            self.image_data["fill"][self.move_data["origin"]] = "#ced179"

            return menu

        async def promotion():
            menu = self.stages[self.PROMOTION]

            for piece_type in pychess.PIECE_TYPES:
                if piece_type != pychess.PAWN:
                    menu.add_option(
                        label=f"{chess.helpers.convert_piece_format(piece_type, 'name').capitalize()}",
                        value=str(piece_type)
                    )

            msg = f"**{self.move_data['piece_type'].capitalize()} " \
                  f"({square_name(self.move_data['origin']).capitalize()})** " \
                  f"will reach its last rank and must be promoted. Choose a piece to promote it to."

            menu.embed = discord.Embed(title="Pawn Promotion", description=msg, color=support.Color.mint())

            self.image_data["fill"].clear()
            self.image_data["lastmove"] = self.get_move()
            self.image_data["arrows"] = [(self.move_data["origin"], self.move_data["destination"])]

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
            with chess.helpers.get_board_png(**self.image_data) as board_png:
                select_menu.embed.set_image(url=f"attachment://{board_png.filename}")
                self.add_item(select_menu)

                self.configure_buttons()

                if interaction:
                    await interaction.response.defer()
                    await interaction.edit_original_message(embed=select_menu.embed, file=board_png, attachments=[],
                                                            view=self)
                else:
                    await self.ctx.defer(ephemeral=True)
                    await self.ctx.respond(embed=select_menu.embed, file=board_png, view=self, ephemeral=True)
        else:
            piece_type = self.move_data["piece_type"]
            origin_square = self.move_data["origin"]
            destination_square = self.move_data["destination"]
            promotion_piece = self.move_data["promotion"]

            move_str = f"- Move **{piece_type.capitalize()} ({square_name(origin_square).capitalize()})** to " \
                       f"**{square_name(destination_square).capitalize()}**"

            if promotion_piece:
                move_str += f"\n- Promote aforementioned {piece_type.capitalize()} to " \
                            f"**{chess.helpers.convert_piece_format(promotion_piece, 'name').capitalize()}**"

            self.clear_items()
            self.configure_buttons()

            msg = "Please confirm the following move:\n\n" + move_str

            embed = discord.Embed(title="Confirm Move", description=msg, color=support.Color.mint())

            self.image_data["fill"].clear()
            self.image_data["lastmove"] = self.get_move()
            self.image_data["arrows"] = [(origin_square, destination_square)]

            with chess.helpers.get_board_png(**self.image_data) as board_png:
                embed.set_image(url=f"attachment://{board_png.filename}")
                await interaction.response.defer()
                await interaction.edit_original_message(embed=embed, file=board_png, attachments=[], view=self)

    async def initiate_selection(self):
        await self.present()
        await self.wait()

        return self.get_move()


class ChessBoardView(EnhancedView):
    class MoveHistoryPaginator:
        def __init__(self, move_history: DoublyLinkedList):
            self.move_history = move_history
            self.current_page = self.move_history.last
            self.page_number = len(move_history)

        def indicator(self):
            return f"{self.page_number}/{len(self.move_history)}"

        def current(self):
            return self.current_page.value

        def first(self):
            self.current_page = self.move_history.first
            self.page_number = 1

        def previous(self):
            self.current_page = self.current_page.prev
            self.page_number -= 1

        def next(self):
            self.current_page = self.current_page.next
            self.page_number += 1

        def last(self):
            self.current_page = self.move_history.last
            self.page_number = len(self.move_history)

        def has_next(self):
            return self.current_page.next is not None

        def has_previous(self):
            return self.current_page.prev is not None

        def __len__(self):
            return len(self.move_history)

    def __init__(self, player: chess.ChessPlayer, **kwargs):
        super().__init__(**kwargs)
        self.player = player

        self.game = self.player.game
        self.history = self.MoveHistoryPaginator(self.game.move_history)
        self.highlight_last_move = False

        self.image_data = {
            "board": self.game.board,
            "orientation": self.player.color,
            "arrows": [],
            "lastmove": None,
            "coordinates": True,
        }

    @discord_button(label="Flip Orientation", custom_id="orientation", style=ButtonStyle.gray, row=2)
    async def flip_orientation(self, button: Button, interaction: Interaction):
        self.image_data["orientation"] = not self.image_data["orientation"]

        await self.present(interaction)

    async def toggle_coordinates(self, interaction: Interaction):
        self.image_data["coordinates"] = not self.image_data["coordinates"]

        button = discord.utils.find(lambda b: b.custom_id == "coordinates", self.children)
        button.label = "Hide Coordinates" if self.image_data["coordinates"] else "Show Coordinates"

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
        button.label = button.label.replace("Highlight", "Unhighlight") if self.image_data[
            "lastmove"] else button.label.replace("Unhighlight", "Highlight")

        await self.present(interaction)

    async def toggle_move_history(self, interaction: Interaction):
        move_history_button: Button = discord.utils.find(lambda b: b.custom_id == "move_history", self.children)
        last_move_button = discord.utils.find(lambda b: b.custom_id == "last_move", self.children)

        if move_history_button.label == "Show Move History":
            move_history_button.label = "Hide Move History"
            last_move_button.label = last_move_button.label.replace("Last ", "")

            first_button = Button(label="", emoji="⏮", style=ButtonStyle.gray, custom_id="history_first", row=1)
            first_button.callback = self.history_first
            self.add_item(first_button)

            previous_button = Button(label="", emoji="⏪", style=ButtonStyle.gray, custom_id="history_previous", row=1)
            previous_button.callback = self.history_previous
            self.add_item(previous_button)

            indicator_button = Button(label=self.history.indicator(), style=ButtonStyle.gray,
                                      custom_id="history_indicator", disabled=True, row=1)
            self.add_item(indicator_button)

            next_button = Button(label="", emoji="⏩", style=ButtonStyle.gray, custom_id="history_next", row=1,
                                 disabled=True)
            next_button.callback = self.history_next
            self.add_item(next_button)

            last_button = Button(label="", emoji="⏭", style=ButtonStyle.gray, custom_id="history_last", row=1,
                                 disabled=True)
            last_button.callback = self.history_last
            self.add_item(last_button)

            await self.present(interaction)

        elif move_history_button.label == "Hide Move History":
            move_history_button.label = "Show Move History"
            last_move_button.label = last_move_button.label.replace("Move", "Last Move")

            self.history.last()
            self.refresh_page()

            button_ids = ["history_first", "history_previous", "history_indicator", "history_next", "history_last"]
            for button_id in button_ids:
                button = discord.utils.find(lambda b: b.custom_id == button_id, self.children)
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

        last_move_button = discord.utils.find(lambda b: b.custom_id == "last_move", self.children)

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

        indicator_button = discord.utils.find(lambda b: b.custom_id == "history_indicator", self.children)
        indicator_button.label = self.history.indicator()

        first_button = discord.utils.find(lambda b: b.custom_id == "history_first", self.children)
        previous_button = discord.utils.find(lambda b: b.custom_id == "history_previous", self.children)
        first_button.disabled = previous_button.disabled = not self.history.has_previous()

        next_button = discord.utils.find(lambda b: b.custom_id == "history_next", self.children)
        last_button = discord.utils.find(lambda b: b.custom_id == "history_last", self.children)
        next_button.disabled = last_button.disabled = not self.history.has_next()

    async def present(self, interaction: Interaction = None):
        with chess.helpers.get_board_png(**self.image_data) as board_png:
            if interaction:
                await interaction.response.defer()
                await interaction.edit_original_message(file=board_png, attachments=[], view=self)
            else:
                await self.ctx.defer(ephemeral=True)
                await self.ctx.respond(file=board_png, view=self, ephemeral=True)

    async def initiate_view(self):
        coordinates_button = Button(label="Hide Coordinates", custom_id="coordinates", style=ButtonStyle.gray, row=2)
        coordinates_button.callback = self.toggle_coordinates
        self.add_item(coordinates_button)

        if len(self.history) > 1:
            last_move_button = Button(label="Highlight Last Move", custom_id="last_move", style=ButtonStyle.gray, row=3)
            last_move_button.callback = self.toggle_move_highlight
            self.add_item(last_move_button)

            move_history_button = Button(label="Show Move History", custom_id="move_history", style=ButtonStyle.gray,
                                         row=3)
            move_history_button.callback = self.toggle_move_history
            self.add_item(move_history_button)

        await self.present()
