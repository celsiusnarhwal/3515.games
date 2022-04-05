from __future__ import annotations

import discord


class Color(discord.Color):
    """
    An extension of Pycord's ``discord.Color`` class that implements additional colors not included with the library.
    Because it subclasses ``discord.Color``, both the standard Pycord colors and the custom colors implemented
    by this class can be accessed from ``Color`` objects, avoiding the need to flip-flop between
    ``Color`` and ``discord.Color``.
    """

    @classmethod
    def mint(cls):
        return cls(0x03cb98)

    @classmethod
    def cyan(cls):
        return cls(0x00ffff)

    @classmethod
    def white(cls):
        return cls(0xffffff)

    @classmethod
    def black(cls):
        return cls(0x000000)


class GamePermissions(discord.Permissions):
    """
    Implements permission set constants for 3515.games.
    """

    # the integers used to instantiate the Permissions objects are obtained from Discord's bot permissions calculator:
    # https://discord.com/developers

    @classmethod
    def universal(cls):
        """
        The set of permissions universally required by all of 3515.games' functionality. All other permission sets
        implemented by :class:`GamePermissions` are *in addition* to this one.

        Returns a :class:`discord.Permissions` object with the following permissions:

        - Read Messages/View Channels
        - Send Messages
        """
        return cls(3072)

    @classmethod
    def rps(cls):
        """
        The set of permissions required for Rock-Paper-Scissors.

        Returns a :class:`discord.Permissions` object with ``GamePermissions.universal()`` and the following permissions:

        - Embed Links
        """
        return cls(cls.universal().value | 16384)

    @classmethod
    def uno_public(cls):
        """
        The set of permissions required for public UNO games.

        Returns a :class:`discord.Permissions` object with ``GamePermissions.universal()`` and the following permissions:

        - Create Public Threads
        - Send Messages in Threads
        - Manage Messages
        - Manage Threads
        - Embed Links
        - Mention @everyone, @here, and All Roles
        - Use External Emojis
        """
        return cls(cls.universal().value | 326417932288)

    @classmethod
    def uno_private(cls):
        """
        The set of permissions required for public UNO games.

        Returns a :class:`discord.Permissions` object with ``GamePermissions.universal()`` and the following permissions:

        - Create Private Threads
        - Send Messages in Threads
        - Manage Messages
        - Manage Threads
        - Embed Links
        - Mention @everyone, @here, and All Roles
        - Use External Emojis
        """
        return cls(cls.universal().value | 360777670656)
