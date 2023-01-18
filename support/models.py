########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import asyncio
import inspect
from typing import Self

import discord
import inflect as ifl
from discord.ext import commands
from path import Path

import support

inflect = ifl.engine()


class HostedMultiplayerGame:
    """
    Consolidates common attributes for hosted multiplayer games. A hosted multiplayer a game is any game that supports
    more than two players where one of those players is deemed the "Game Host".

    Parameters
    ----------
    guild: discord.Guild
        The guild in which the game is being played.
    thread: discord.Thread
        The thread in which the game is being played.
    host: discord.User
        The user who is the Game Host.

    Attributes
    ----------
    name: str
        The full name of the game.
    short_name: str
        The short name of the game. Unless explicitly defined, this will be the same as the full name.
    min_players: int
        The minimum number of players required to play the game.
    lobby_intro_msg: discord.Message
        The introduction message sent to the game thread when the game is created.
    __all_games__: dict
        A dictionary that maps game objects to the IDs of the threads in which they are being played.
    """

    name = ""
    short_name = name

    __all_games__ = dict()

    def __init__(
        self,
        guild: discord.Guild,
        thread: discord.Thread,
        host: discord.User,
        *args,
        **kwargs,
    ):
        self.guild = guild
        self.thread = thread
        self.host = host

        self.short_name = self.short_name or self.name

        self.lobby_intro_msg = None
        self.min_players = 2
        self.voice_channel: discord.VoiceChannel = None

        self.__all_games__[self.thread.id] = self

    @classmethod
    def retrieve_game(cls, thread_id) -> HostedMultiplayerGame | None:
        """
        Retrieves a game given the unique identifier of its associated game thread.

        :param thread_id: The unique identifier of the game's associated thread.
        :return: The UnoGame object associated with the passed-in thread ID if one exists; otherwise None.
        """
        return cls.__all_games__.get(thread_id)

    @classmethod
    def find_hosted_games(
        cls, user: discord.User, guild_id: int
    ) -> HostedMultiplayerGame | None:
        """
        Retrieves games where the Game Host is a particular user and that are taking place in a
        particular server.

        :param user: The Game Host to look for.
        :param guild_id: The unique identifier of the server to search for games in.
        :return: An ``UnoGame`` object associated with the specified Game Host and server if one exists; otherwise None.
        """
        return discord.utils.find(
            lambda g: g.host == user and g.guild.id == guild_id,
            cls.__all_games__.values(),
        )

    @classmethod
    def verify_unique_host(cls):
        """
        A decorator used to check that a user attempting to create a game is not already hosting one in the same
        server.
        """

        async def predicate(ctx: discord.ApplicationContext):
            user_hosted_game = cls.find_hosted_games(
                user=ctx.user, guild_id=ctx.guild_id
            )

            if not user_hosted_game:
                return True
            else:
                message = (
                    f"You're already hosting {inflect.a(cls.name)} game in this server. "
                    f"Before you can create a new one, you must either complete, end, or transfer host powers "
                    f"for your current game.\n"
                )
                embed = discord.Embed(
                    title="You're already hosting a game.",
                    description=message,
                    color=Color.red(),
                )
                await ctx.respond(
                    embed=embed,
                    view=support.views.GameThreadURLView(
                        thread=user_hosted_game.thread
                    ),
                    ephemeral=True,
                )

                return False

        return commands.check(predicate)

    async def transfer_host(self, new_host: discord.User):
        """
        Transfers Game Host privileges from one user to another.

        :param new_host: The user to transfer host privileges to.
        """
        old_host = self.host
        self.host = new_host

        embed = discord.Embed(
            title="The Game Host has changed!",
            description=f"{old_host.mention} has transferred host powers to {new_host.mention}. "
            f"{new_host.mention} is now the Game Host.",
            color=support.Color.orange(),
        )

        await self.thread.send(content="@everyone", embed=embed)

        await self.thread.edit(
            name=self.thread.name.replace(old_host.name, new_host.name)
        )

        intro = self.lobby_intro_msg
        intro_0 = intro.embeds[0]
        intro_0.title = intro_0.title.replace(old_host.name, new_host.name)
        intro_0.description = intro_0.description.replace(
            old_host.mention, new_host.mention
        )
        intro.embeds[0] = intro_0
        await self.lobby_intro_msg.edit(embeds=intro.embeds)

    async def force_close(self, reason):
        """
        Force closes a game.
        :param reason: The reason why the game is being closed ("host_abortion, "thread_deletion", "channel_deletion",
        "host_left", "insufficient_players", "inactivity", or "time_limit").
        """
        self.__all_games__.pop(self.thread.id)

        async def host_abortion():
            """
            Aborts an game.
            """
            thread_msg = (
                f"The Game Host, {self.host.mention}, has ended this {self.name} game.\n"
                f"\n"
                f"This thread has been locked and will be automatically deleted in 60 seconds."
            )
            thread_embed = discord.Embed(
                title=f"The Game Host has ended this {self.name} game.",
                description=thread_msg,
                color=Color.red(),
                timestamp=discord.utils.utcnow(),
            )

            await self.thread.edit(
                name=f"{self.short_name} with {self.host.name} - Game Over!"
            )
            msg = await self.thread.send(embed=thread_embed)
            await msg.pin()

        async def thread_deletion():
            """
            Force closes a game in the event that its associated thread is deleted.
            """
            msg = (
                f"Your {self.name} game in {self.guild.name} was automatically closed because its game "
                f"thread was deleted."
            )
            embed = discord.Embed(
                title=f"Your {self.name} game was automatically closed.",
                description=msg,
                color=Color.red(),
                timestamp=discord.utils.utcnow(),
            )

            await self.host.send(embed=embed)

        async def channel_deletion():
            """
            Force closes a game in the event that the parent channel of its associated thread is deleted.
            """
            msg = (
                f"Your {self.name} game in {self.guild.name} was automatically closed because the parent "
                f"channel of its game thread was deleted."
            )
            embed = discord.Embed(
                title="Your {self.name} game was automatically closed.",
                description=msg,
                color=Color.red(),
                timestamp=discord.utils.utcnow(),
            )

            await self.host.send(embed=embed)

        async def host_left():
            """
            Force closes a game in the event that the Game Host leaves its associated thread.
            """
            thread_msg = (
                f"This {self.name} game has been automatically closed because the Game Host, "
                f"{self.host.mention}, left.\n"
                f"\n"
                f"This thread has been locked and will be automatically deleted in 60 seconds."
            )
            thread_embed = discord.Embed(
                title=f"This {self.name} game has been automatically closed.",
                description=thread_msg,
                color=Color.red(),
                timestamp=discord.utils.utcnow(),
            )

            host_msg = (
                f"Your {self.name} game in {self.guild.name} was automatically closed because you left "
                f"either the game or its associated thread."
            )
            host_embed = discord.Embed(
                title=f"Your {self.name} game was automatically closed.",
                description=host_msg,
                color=Color.red(),
                timestamp=discord.utils.utcnow(),
            )

            await self.thread.edit(
                name=f"{self.short_name} with {self.host.name} - Game Over!"
            )
            msg = await self.thread.send(embed=thread_embed)
            await msg.pin()

            await self.host.send(embed=host_embed)

        async def insufficient_players():
            """
            Force closes a game in the event that there are insufficient players to continue.
            """
            thread_msg = (
                f"This {self.name} game has been automatically closed because there are not enough "
                f"players remaining for it to continue.\n"
                f"\n"
                f"This thread has been locked and will be automatically deleted in 60 seconds."
            )
            thread_embed = discord.Embed(
                title=f"This {self.name} game has been automatically closed.",
                description=thread_msg,
                color=Color.red(),
                timestamp=discord.utils.utcnow(),
            )

            host_msg = (
                f"Your {self.name} game in {self.guild.name} was automatically closed due to insufficient "
                f"players."
            )
            host_embed = discord.Embed(
                title=f"Your {self.name} game was automatically closed.",
                description=host_msg,
                color=Color.red(),
                timestamp=discord.utils.utcnow(),
            )

            await self.thread.edit(
                name=f"{self.short_name} with {self.host.name} - Game Over!"
            )
            msg = await self.thread.send(embed=thread_embed)
            await msg.pin()

            await self.host.send(embed=host_embed)

        async def inactivity():
            thread_msg = (
                f"This {self.name} game has been automatically closed due to inactivity.\n"
                "\n"
                "This thread has been locked and will be automatically deleted in 60 seconds."
            )
            thread_embed = discord.Embed(
                title=f"This {self.name} game has been automatically closed.",
                description=thread_msg,
                color=Color.red(),
                timestamp=discord.utils.utcnow(),
            )

            host_msg = f"Your {self.name} game in {self.guild.name} was automatically closed due to inactivity."
            host_embed = discord.Embed(
                title=f"Your {self.name} game was automatically closed.",
                description=host_msg,
                color=Color.red(),
                timestamp=discord.utils.utcnow(),
            )

            await self.thread.edit(
                name=f"{self.short_name} with {self.host.name} - Game Over!"
            )
            msg = await self.thread.send(embed=thread_embed)
            await msg.pin()

            await self.host.send(embed=host_embed)

        async def time_limit():
            thread_msg = (
                f"This {self.name} game has been automatically closed because it took "
                f"too long to complete.\n"
                f"\n"
                "This thread has been locked and will be automatically deleted in 60 seconds."
            )
            thread_embed = discord.Embed(
                title="This {self.name} game has been automatically closed.",
                description=thread_msg,
                color=Color.red(),
                timestamp=discord.utils.utcnow(),
            )

            host_msg = (
                f"Your {self.name} game in {self.guild.name} was automatically closed because it took "
                f"too long to complete.\n"
            )
            host_embed = discord.Embed(
                title="Your {self.name} game was automatically closed.",
                description=host_msg,
                color=Color.red(),
                timestamp=discord.utils.utcnow(),
            )

            await self.thread.edit(
                name=f"{self.short_name} with {self.host.name} - Game Over!"
            )
            msg = await self.thread.send(embed=thread_embed)
            await msg.pin()

            await self.host.send(embed=host_embed)

        reason_map = {
            "host_abortion": host_abortion,
            "channel_deletion": channel_deletion,
            "thread_deletion": thread_deletion,
            "host_left": host_left,
            "insufficient_players": insufficient_players,
            "inactivity": inactivity,
            "time_limit": time_limit,
        }

        await reason_map[reason]()

        await self.thread.archive(locked=True)
        await asyncio.sleep(60)
        await self.thread.delete()

    async def create_voice_channel(self) -> discord.VoiceChannel:
        guild_categories = self.guild.by_category()
        my_category = discord.utils.find(
            lambda c: c[0] is not None and c[0].name.casefold() == "3515.games",
            guild_categories,
        )
        if my_category:
            my_category = my_category[0]
        else:
            my_category = await self.guild.create_category(
                "3515.games", position=len(guild_categories) + 1
            )

        overwrites = {
            self.guild.me: discord.PermissionOverwrite.from_pair(
                allow=support.GamePermissions.vc(), deny=discord.Permissions.none()
            ),
            self.host: discord.PermissionOverwrite.from_pair(
                allow=support.GamePermissions.vc(), deny=discord.Permissions.none()
            ),
            self.guild.default_role: discord.PermissionOverwrite.from_pair(
                allow=discord.Permissions.none(), deny=support.GamePermissions.vc()
            ),
        }

        self.voice_channel = await my_category.create_voice_channel(
            f"{self.short_name} with {self.host.name}!", overwrites=overwrites
        )

        embed = discord.Embed(
            title="Nothing to see (or say) here.",
            description="You should head to the game thread instead.",
            color=support.Color.red(),
        )

        await self.voice_channel.send(
            embed=embed, view=support.GameThreadURLView(self.thread)
        )

        return self.voice_channel


class BasePlayer:
    """
    The base class for objects representing players in a game.
    """

    def __init__(self, user: discord.Member, *args, **kwargs):
        self.user = user

    @property
    def name(self) -> str:
        return self.user.name

    @property
    def mention(self) -> str:
        return self.user.mention

    def __str__(self):
        return self.name


class Color(discord.Color):
    """
    An extension of Pycord's ``discord.Color`` class that implements additional colors not included with the library.
    """

    @classmethod
    def mint(cls):
        return cls(0x03CB98)

    @classmethod
    def white(cls):
        return cls(0xFFFFFF)

    @classmethod
    def black(cls):
        return cls(0x000000)


class Assets(Path):
    """
    Implements context managers that point to asset directories for 3515.games.
    """

    @classmethod
    def _get_pointer(cls, module) -> Self:
        return cls.joinpath("cogs", module, "assets")

    @classmethod
    def about(cls):
        return cls._get_pointer("about")

    @classmethod
    def rps(cls):
        return cls._get_pointer("rps")

    @classmethod
    def uno(cls):
        return cls._get_pointer("uno")

    @classmethod
    def chess(cls):
        return cls._get_pointer("chess")

    @classmethod
    def cah(cls):
        return cls._get_pointer("cah")

    @classmethod
    def kurisu(cls):
        return cls("kurisu/assets")


class GamePermissions(discord.Permissions):
    """
    Implements permission set constants for 3515.games.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update(read_messages=True, send_messages=True)

    @classmethod
    def universal(cls):
        """
        The set of permissions universally required by all of 3515.games' functionality.

        Returns a :class:`GamePermissions` object with the following permissions:

        - Read Messages/View Channels
        - Send Messages
        """
        return cls(3072)

    @classmethod
    def rps(cls):
        """
        The set of permissions required for Rock-Paper-Scissors.

        Returns a :class:`GamePermissions` object with the following permissions:

        - Read Messages/View Channels
        - Send Messages
        - Embed Links
        - Attach Files
        """
        return cls(49152)

    @classmethod
    def uno(cls):
        """
        The set of permissions required for UNO games.

        Returns a :class:`GamePermissions` object with the permissions:

        - Read Messages/View Channels
        - Send Messages
        - Create Public Threads
        - Send Messages in Threads
        - Manage Messages
        - Manage Threads
        - Embed Links
        - Attach Files
        - Mention @everyone, @here, and All Roles
        - Use External Emojis
        """
        return cls.universal() + cls(326417965056)

    @classmethod
    def chess(cls):
        """
        The set of permissions required for chess.

        Returns a :class:`GamePermissions` object with the following
        permissions:

        - Read Messages/View Channels
        - Send Messages
        - Create Public Threads
        - Send Messages in Threads
        - Manage Messages
        - Manage Threads
        - Embed Links
        - Attach Files
        - Use External Emojis
        """
        return cls.universal() + cls(326417833984)

    @classmethod
    def cah(cls):
        """
        The set of permissions required for public CAH games. This is currently equivalent to
        ``GamePermissions.uno()``.

        Returns a :class:`GamePermissions` object with the following permissions:

        - Read Messages/View Channels
        - Send Messages
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
    def cah_voice(cls):
        """
        The set of permissions required for CAH games whose hosts choose to equip them with private,
        bot-controlled, voice channels. These permissions are required *in addition* to ``GamePermissions.cah()``,
        even though ``GamePermissions.cah()`` is not a subset of these permissions.

        Returns a :class:`GamePermissions` object with ``GamePermissions.universal()`` and the following
        permissions:

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
    def vc(cls):
        """
        The set of permissions required to create voice channels for supported games.

        Returns a :class:`GamePermissions` object with the following permissions:

        - Read Messages/View Channels
        - Send Messages
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
    def everything(cls):
        """
        Returns a :class:`GamePermissions` object with the combined set of all other predefined permission sets in the
        class.
        """
        permissions = cls.none()

        permsets = [
            permset
            for name, permset in inspect.getmembers(cls, inspect.ismethod)
            if name in cls.__dict__
            and name
            != "everything"  # everybody gangsta till the https://youtu.be/CVCTz3Xc__s
        ]

        for permset in permsets:
            permissions += permset()

        return permissions

    def __iter__(self):
        # god bless python
        return self.__class__.__base__.__iter__(self.__class__.__base__(self.value))


class Pseudocommand(discord.commands.SlashCommand):
    """
    A pseudocommand.

    Notes
    -----
    Pseudocommands are corountines that are treated like commands at the code level but are not actually accessible
    to end users. 3515.games uses a custom subclass of :class:`discord.bot.Bot` that blocks the registration
    of pseudocommands with the Discord API.

    Unlike regular commands, pseudocommands can be called directly without losing their checks.
    """

    async def __call__(self, ctx, *args, **kwargs):
        if await self.can_run(ctx):
            return await super().__call__(*args, **kwargs)
