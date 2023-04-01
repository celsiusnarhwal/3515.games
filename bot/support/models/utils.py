########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import inspect
import operator

import discord
from natsu import sum
from path import Path

from gps import Routes
from keyboard import *

__all__ = ["Color", "Assets", "GamePermissions"]


class Color(discord.Color):
    """
    An extension of :class:`discord.Color` with some additional colors.
    """

    @classmethod
    def mint(cls) -> Self:
        return cls(0x03CB98)

    @classmethod
    def white(cls) -> Self:
        return cls(0xFFFFFF)

    @classmethod
    def black(cls) -> Self:
        return cls(0x000000)

    @classmethod
    def violet(cls) -> Self:
        return cls(0xAC7FE0)

    @classmethod
    def caution(cls) -> Self:
        return cls.orange()

    @classmethod
    def error(cls) -> Self:
        return cls.red()


class Assets(Path):
    """
    Context managers for switching in and out of asset directories.
    """

    @classmethod
    def _get(cls, module) -> Self:
        return cls.joinpath(Routes.bot(), "cogs", module, "assets")

    @classmethod
    def misc(cls) -> Self:
        return cls._get("misc")

    @classmethod
    def rps(cls) -> Self:
        return cls._get("rps")

    @classmethod
    def uno(cls) -> Self:
        return cls._get("uno")

    @classmethod
    def chess(cls) -> Self:
        return cls._get("chess")

    @classmethod
    def cah(cls) -> Self:
        return cls._get("cah")

    @classmethod
    def kurisu(cls) -> Self:
        return cls.joinpath(Routes.kurisu(), "assets")


class GamePermissions(discord.Permissions):
    """
    Permissions constants.

    Notes
    -----
    All objects of this class contain the Read Messages/View Channels and Send Messages permissions at a minimum.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update(read_messages=True, send_messages=True)

    @classmethod
    def universal(cls) -> Self:
        return cls()

    @classmethod
    def rps(cls) -> Self:
        """
        The set of permissions required for Rock-Paper-Scissors.

        Returns a :class:`GamePermissions` object with the following permissions:

        - Embed Links
        - Attach Files
        """
        return cls(49152)

    @classmethod
    def uno(cls) -> Self:
        """
        The set of permissions required for UNO games.

        Returns a :class:`GamePermissions` object with the permissions:

        - Create Public Threads
        - Send Messages in Threads
        - Manage Messages
        - Manage Threads
        - Embed Links
        - Attach Files
        - Mention @everyone, @here, and All Roles
        - Use External Emojis
        """
        return cls(326417965056)

    @classmethod
    def chess(cls) -> Self:
        """
        The set of permissions required for chess.

        Returns a :class:`GamePermissions` object with the following
        permissions:

        - Create Public Threads
        - Send Messages in Threads
        - Manage Messages
        - Manage Threads
        - Embed Links
        - Attach Files
        - Use External Emojis
        """
        return cls(326417833984)

    @classmethod
    def cah(cls) -> Self:
        """
        The set of permissions required for public CAH games. This is currently equivalent to
        ``GamePermissions.uno()``.

        Returns a :class:`GamePermissions` object with the following permissions:

        - Create Public Threads
        - Send Messages in Threads
        - Manage Messages
        - Manage Threads
        - Embed Links
        - Attach Files
        - Mention @everyone, @here, and All Roles
        - Use External Emojis
        """
        return cls.uno()

    @classmethod
    def vc(cls) -> Self:
        """
        The set of permissions required to create voice channels for supported games.

        Returns a :class:`GamePermissions` object with the following permissions:

        - Manage Channels
        - Read Message History
        - Connect
        - Speak
        - Mute Members
        - Deafen Members
        - Move Members
        - Use Voice Activity
        - Priority Speaker

        """
        return cls.voice() + cls.read_message_history + cls.manage_channels - cls.stream

    @classmethod
    def everything(cls) -> Self:
        """
        Returns a :class:`GamePermissions` object with the combined set of all other predefined permission sets in the
        class.
        """
        return sum(
            [
                permset()
                for name, permset in inspect.getmembers(cls, inspect.ismethod)
                if name in vars(cls) and name != "everything"
            ]
        )

    @staticmethod
    def _bitmath(op: Callable):
        def wrapper(self, other):
            cls = type(self)
            return cls(op(cls.__base__(self.value), other).value)

        return wrapper

    __and__ = _bitmath(operator.and_)
    __or__ = _bitmath(operator.or_)
    __sub__ = _bitmath(operator.sub)

    def __iter__(self):
        cls = type(self)
        return cls.__base__.__iter__(cls.__base__(self.value))
