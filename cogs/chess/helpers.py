import os
import tempfile
from contextlib import contextmanager

import chess as pychess
import chess.svg as pychess_svg
import discord
from path import Path
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg


@contextmanager
def get_board_png(board: pychess.Board) -> discord.File:
    directory = Path(tempfile.mkdtemp())

    with directory:
        with open("board.svg", "w+") as svg:
            svg.write(pychess_svg.board(board, size=1800))
            renderPM.drawToFile(svg2rlg("board.svg"), "board.png", fmt="png")

        yield discord.File(os.path.abspath("board.png"), filename="board.png")

    directory.rmtree()
