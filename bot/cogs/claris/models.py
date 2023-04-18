from __future__ import annotations

from attrs import define
from elysia import Fields
from PIL import Image, ImageDraw

from keyboard import *
from support import BasePlayer, ThreadedGame


@define
class ClarisGame(ThreadedGame):
    __games__: ClassVar[dict[int, Self]]

    name: ClassVar = "Connect 4"

    players: list[ClarisPlayer]

    has_started: bool = Fields.attr(default=False)
    current_player: ClarisPlayer = Fields.attr(default=None)
    turn_number: int = Fields.attr(default=0)
    turn_uuid: int = Fields.attr(default=0)
    red: ClarisPlayer = Fields.attr(default=None)
    yellow: ClarisPlayer = Fields.attr(default=None)

    async def force_close(self, *args, **kwargs):
        pass

    async def retrieve_player(self, *args, **kwargs):
        pass

    async def open_lobby(self, *args, **kwargs):
        pass


class ClarisPlayer(BasePlayer):
    ...


@define
class ClarisBoard:
    width: ClassVar[int] = 400
    height: ClassVar[int] = 400
    color: ClassVar[tuple[int]] = (40, 84, 198)
    hole_diameter: ClassVar[int] = 80
    hole_padding: ClassVar[int] = 10
    hole_color: ClassVar[tuple[int]] = (255, 255, 255)
    red_color: ClassVar[tuple[int]] = (255, 0, 0)
    yellow_color: ClassVar[tuple[int]] = (255, 255, 0)

    image: Image.Image

    @classmethod
    def new(cls) -> Self:
        board = Image.new("RGB", (cls.width, cls.height), cls.color)
        draw = ImageDraw.Draw(board)

        for col in range(7):
            for row in range(6):
                x = cls.hole_padding + col * (cls.hole_diameter + cls.hole_padding)
                y = cls.hole_padding + row * (cls.hole_diameter + cls.hole_padding)
                draw.ellipse(
                    (x, y, x + cls.hole_diameter, y + cls.hole_diameter),
                    fill=cls.hole_color,
                )

        return cls(board)
