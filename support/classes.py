from __future__ import annotations

import asyncio
import os
from typing import Union

import discord
from path import Path


class HostedMultiplayerGame:
    __all_games__ = dict()

    def __init__(self, guild: discord.Guild, thread: discord.Thread, host: discord.User):
        self.guild = guild
        self.thread = thread
        self.host = host

        self.name = ""

        self.__all_games__[self.thread.id] = self

    @classmethod
    def retrieve_game(cls, thread_id) -> Union[HostedMultiplayerGame, None]:
        """
        Retrieves a game given the unique identifier of its associated game thread.

        :param thread_id: The unique identifier of the game's associated thread.
        :return: The UnoGame object associated with the passed-in thread ID if one exists; otherwise None.
        """
        return cls.__all_games__.get(thread_id)

    @classmethod
    def find_hosted_games(cls, user: discord.User, guild_id: int) -> Union[HostedMultiplayerGame, None]:
        """
        Retrieves games where the Game Host is a particular user and that are taking place in a
        particular server.

        :param user: The Game Host to look for.
        :param guild_id: The unique identifier of the server to search for games in.
        :return: An ``UnoGame`` object associated with the specified Game Host and server if one exists; otherwise None.
        """
        return next((game for game in cls.__all_games__.values() if
                     game.host == user and game.guild.id == guild_id),
                    None)

    async def force_close(self, reason=None):
        """
        Force closes a game.
        :param reason: The reason why the game is being closed ("thread_deletion", "channel_deletion", "host_left",
        "players_left", "inactivity", or "time_limit").
        """

        self.__all_games__.pop(self.thread.id)

        async def thread_deletion():
            """
            Force closes z game in the event that its associated thread is deleted.
            """
            msg = f"Your {self.name} game in {self.guild.name} was automatically closed because its game " \
                  f"thread was deleted."
            embed = discord.Embed(title=f"Your {self.name} game was automatically closed.", description=msg,
                                  color=Color.red(), timestamp=discord.utils.utcnow())

            await self.host.send(embed=embed)

        async def channel_deletion():
            """
            Force closes a game in the event that the parent channel of its associated thread is deleted.
            """
            msg = f"Your {self.name} game in {self.guild.name} was automatically closed because the parent " \
                  f"channel of its game thread was deleted."
            embed = discord.Embed(title="Your {self.name} game was automatically closed.", description=msg,
                                  color=Color.red(), timestamp=discord.utils.utcnow())

            await self.host.send(embed=embed)

        async def host_left():
            """
            Force closes a game in the event that the Game Host leaves its associated thread.
            """
            thread_msg = f"This {self.name} game has been automatically closed because the Game Host, " \
                         f"{self.host.mention}, left.\n" \
                         f"\n" \
                         f"This thread has been locked and will be automatically deleted in 60 seconds."
            thread_embed = discord.Embed(title=f"This {self.name} game has been automatically closed.",
                                         description=thread_msg,
                                         color=Color.red(), timestamp=discord.utils.utcnow())

            host_msg = f"Your {self.name} game in {self.guild.name} was automatically closed because you left " \
                       f"either the game or its associated thread."
            host_embed = discord.Embed(title=f"Your {self.name} game was automatically closed.", description=host_msg,
                                       color=Color.red(), timestamp=discord.utils.utcnow())

            await self.thread.edit(name=f"{self.name} with {self.host.name} - Game Over!")
            msg = await self.thread.send(embed=thread_embed)
            await msg.pin()
            await self.thread.archive(locked=True)

            await self.host.send(embed=host_embed)

            await asyncio.sleep(60)
            await self.thread.delete()

        async def players_left():
            """
            Force closes a game in the event that all players aside from the Game Host leave the game.
            """
            thread_msg = f"This {self.name} game has been automatically closed because all players left.\n" \
                         f"\n" \
                         f"This thread has been locked and will be automatically deleted in 60 seconds."
            thread_embed = discord.Embed(title=f"This {self.name} game has been automatically closed.",
                                         description=thread_msg,
                                         color=Color.red(), timestamp=discord.utils.utcnow())

            host_msg = f"Your {self.name} game in {self.guild.name} was automatically closed due to insufficient " \
                       f"players."
            host_embed = discord.Embed(title="Your {self.name} game was automatically closed.", description=host_msg,
                                       color=Color.red(), timestamp=discord.utils.utcnow())

            await self.thread.edit(name=f"{self.name} with {self.host.name} - Game Over!")
            msg = await self.thread.send(embed=thread_embed)
            await msg.pin()
            await self.thread.archive(locked=True)

            await self.host.send(embed=host_embed)

            await asyncio.sleep(60)
            await self.thread.delete()

        async def inactivity():
            thread_msg = f"This {self.name} game has been automatically closed due to inactivity.\n" \
                         "\n" \
                         "This thread has been locked and will be automatically deleted in 60 seconds."
            thread_embed = discord.Embed(title="This {self.name} game has been automatically closed.",
                                         description=thread_msg,
                                         color=Color.red(), timestamp=discord.utils.utcnow())

            host_msg = f"Your {self.name} game in {self.guild.name} was automatically closed due to inactivity."
            host_embed = discord.Embed(title="Your {self.name} game was automatically closed.", description=host_msg,
                                       color=Color.red(), timestamp=discord.utils.utcnow())

            await self.thread.edit(name=f"{self.name} with {self.host.name} - Game Over!")
            msg = await self.thread.send(embed=thread_embed)
            await msg.pin()
            await self.thread.archive(locked=True)

            await self.host.send(embed=host_embed)

            await asyncio.sleep(60)
            await self.thread.delete()

        async def time_limit():
            thread_msg = f"This {self.name} game has been automatically closed because it took " \
                         f"too long to complete.\n" \
                         f"\n" \
                         "This thread has been locked and will be automatically deleted in 60 seconds."
            thread_embed = discord.Embed(title="This {self.name} game has been automatically closed.",
                                         description=thread_msg,
                                         color=Color.red(), timestamp=discord.utils.utcnow())

            host_msg = f"Your {self.name} game in {self.guild.name} was automatically closed because it took " \
                       f"too long to complete.\n"
            host_embed = discord.Embed(title="Your {self.name} game was automatically closed.", description=host_msg,
                                       color=Color.red(), timestamp=discord.utils.utcnow())

            await self.thread.edit(name=f"{self.name} with {self.host.name} - Game Over!")
            msg = await self.thread.send(embed=thread_embed)
            await msg.pin()
            await self.thread.archive(locked=True)

            await self.host.send(embed=host_embed)

            await asyncio.sleep(60)
            await self.thread.delete()

            reason_map = {
                "channel_deletion": channel_deletion,
                "thread_deletion": thread_deletion,
                "host_left": host_left,
                "players_left": players_left,
                "inactivity": inactivity,
                "time_limit": time_limit,
            }

            await reason_map[reason]()


class Color(discord.Color):
    """
    An extension of Pycord's ``discord.Color`` class that implements additional colors not included with the library.
    Because it subclasses ``discord.Color``, both the standard Pycord colors and the custom colors implemented
    by this class can be accessed from the ``Color`` class, avoiding the need to flip-flop between
    ``Color`` and ``discord.Color``.
    """

    @classmethod
    def mint(cls):
        return cls(0x03cb98)

    @classmethod
    def white(cls):
        return cls(0xffffff)

    @classmethod
    def black(cls):
        return cls(0x000000)


class Assets(Path):
    """
    Implements context managers that point to asset directories for 3515.games.
    """

    @classmethod
    def get_pointer(cls, module):
        return cls(os.path.join("cogs", module, "assets"))

    @classmethod
    def about(cls):
        return cls.get_pointer("about")

    @classmethod
    def rps(cls):
        return cls.get_pointer("rps")

    @classmethod
    def uno(cls):
        return cls.get_pointer("uno")

    @classmethod
    def chess(cls):
        return cls.get_pointer("chess")


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

        Returns a :class:`discord.Permissions` object with ``GamePermissions.universal()`` and the following
        permissions:

        - Embed Links
        - Attach Files
        """
        return cls(cls.universal().value | 49152)

    @classmethod
    def uno_public(cls):
        """
        The set of permissions required for public UNO games.

        Returns a :class:`discord.Permissions` object with ``GamePermissions.universal()`` and the following
        permissions:

        - Create Public Threads
        - Send Messages in Threads
        - Manage Messages
        - Manage Threads
        - Embed Links
        - Attach Files
        - Mention @everyone, @here, and All Roles
        - Use External Emojis
        """
        return cls(cls.universal().value | 326417965056)

    @classmethod
    def uno_private(cls):
        """
        The set of permissions required for public UNO games.

        Returns a :class:`discord.Permissions` object with ``GamePermissions.universal()`` and the following
        permissions:

        - Create Private Threads
        - Send Messages in Threads
        - Manage Messages
        - Manage Threads
        - Embed Links
        - Attach Files
        - Mention @everyone, @here, and All Roles
        - Use External Emojis
        """
        return cls(cls.universal().value | 360777703424)

    @classmethod
    def chess(cls):
        """
        The set of permissions required for chess.

        Returns a :class:`discord.Permissions` object with ``GamePermissions.universal()`` and the following
        permissions:

        - Create Public Threads
        - Send Messages in Threads
        - Manage Messages
        - Manage Threads
        - Embed Links
        - Attach Files
        - Use External Emojis
        """
        return cls(cls.universal().value | 326417833984)
