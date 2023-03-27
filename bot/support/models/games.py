########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import asyncio
import random
from abc import ABC, abstractmethod
from collections import defaultdict

import aiohttp
import discord
import inflect as ifl
import tomlkit as toml
from attrs import define
from discord.ext import commands
from elysia import Fields
from pydantic import validate_arguments

import support
from keyboard import *
from support.models.pronouns import Pronoun, PronounType

inflect = ifl.engine()


@define
class ThreadedGame(ABC):
    __games__: ClassVar[dict[int, Self]]

    name: ClassVar[str] = ...
    short_name: ClassVar[str] = name

    guild: discord.Guild = Fields.field(frozen=True)
    thread: discord.Thread = Fields.field(frozen=True)

    def __attrs_post_init__(self):
        self.__games__[self.thread.id] = self

    @classmethod
    def retrieve_game(cls, thread_id) -> Self | None:
        """
        Retrieves a game given the unique identifier of its associated game thread.

        Parameters
        ----------
        thread_id: int
            The unique identifier of the game thread.

        Returns
        -------
        Self | None
            The game associated with the specified game thread if one exists; otherwise None.
        """
        return cls.__games__.get(thread_id)

    def kill(self):
        """
        Remove the game from :attr:`__games__`.
        """
        type(self).__games__.pop(self.thread.id)

    @abstractmethod
    async def force_close(self, *args, **kwargs):
        ...

    @abstractmethod
    async def retrieve_player(self, *args, **kwargs):
        ...

    @abstractmethod
    async def open_lobby(self, *args, **kwargs):
        ...


@define
class HostedGame(ThreadedGame, ABC):
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
    """

    min_players: ClassVar[int]

    host: discord.Member

    is_joinable: bool = Fields.attr(default=True)
    lobby_intro_msg: discord.Message = Fields.attr(default=None)
    voice_channel: discord.VoiceChannel = Fields.attr(default=None)

    @classmethod
    def find_hosted_games(cls, user: discord.User, guild_id: int) -> Self | None:
        """
        Retrieves games where the Game Host is a particular user and that are taking place in a
        particular server.

        Parameters
        ----------
        user: discord.User
            The user to search for.
        guild_id: int
            The unique identifier of the server to search in.

        Returns
        -------
        Self | None
            The game where the Game Host is the specified user and that is taking place in the specified server if one
            exists; otherwise None.
        """
        return discord.utils.find(
            lambda g: g.host == user and g.guild.id == guild_id,
            cls.__games__.values(),
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
                    color=support.Color.error(),
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
            color=support.Color.caution(),
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
        self.kill()

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
                color=support.Color.error(),
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
                color=support.Color.error(),
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
                color=support.Color.error(),
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
                color=support.Color.error(),
                timestamp=discord.utils.utcnow(),
            )

            host_msg = (
                f"Your {self.name} game in {self.guild.name} was automatically closed because you left "
                f"either the game or its associated thread."
            )
            host_embed = discord.Embed(
                title=f"Your {self.name} game was automatically closed.",
                description=host_msg,
                color=support.Color.error(),
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
                color=support.Color.error(),
                timestamp=discord.utils.utcnow(),
            )

            host_msg = (
                f"Your {self.name} game in {self.guild.name} was automatically closed due to insufficient "
                f"players."
            )
            host_embed = discord.Embed(
                title=f"Your {self.name} game was automatically closed.",
                description=host_msg,
                color=support.Color.error(),
                timestamp=discord.utils.utcnow(),
            )

            msg = await self.thread.send(embed=thread_embed)
            await msg.pin()
            await self.host.send(embed=host_embed)

            await self.thread.edit(
                name=f"{self.short_name} with {self.host.name} - Game Over!"
            )

        async def inactivity():
            thread_msg = (
                f"This {self.name} game has been automatically closed due to inactivity.\n"
                "\n"
                "This thread has been locked and will be automatically deleted in 60 seconds."
            )
            thread_embed = discord.Embed(
                title=f"This {self.name} game has been automatically closed.",
                description=thread_msg,
                color=support.Color.error(),
                timestamp=discord.utils.utcnow(),
            )

            host_msg = f"Your {self.name} game in {self.guild.name} was automatically closed due to inactivity."
            host_embed = discord.Embed(
                title=f"Your {self.name} game was automatically closed.",
                description=host_msg,
                color=support.Color.error(),
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
                color=support.Color.error(),
                timestamp=discord.utils.utcnow(),
            )

            host_msg = (
                f"Your {self.name} game in {self.guild.name} was automatically closed because it took "
                f"too long to complete.\n"
            )
            host_embed = discord.Embed(
                title="Your {self.name} game was automatically closed.",
                description=host_msg,
                color=support.Color.error(),
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
            color=support.Color.error(),
        )

        await self.voice_channel.send(
            embed=embed, view=support.GameThreadURLView(thread=self.thread)
        )

        return self.voice_channel

    @abstractmethod
    def kick_player(self, *args, **kwargs):
        ...

    @property
    def has_started(self):
        """
        Convenience property to check if the game has started.

        Returns the opposite of :attr:`is_joinable`.
        """
        return not self.is_joinable


@define
class BasePlayer:
    """
    Base class for objects representing players in a game.
    """

    user: discord.Member = Fields.field(frozen=True)

    pronouns: PronounType = Fields.attr(default=PronounType.GENDER_NEUTRAL)

    def __attrs_post_init__(self):
        self.pronouns = asyncio.run(self._genderfabriken())

    @property
    def name(self) -> str:
        """
        The username of the player's associated user.
        """
        return self.user.name

    @property
    def id(self) -> int:
        """
        The ID of the player's associated user.
        """
        return self.user.id

    @property
    def mention(self) -> str:
        """
        The mention string of the player's associated user (e.g. <@170966436125212673>).
        """
        return self.user.mention

    @property
    def avatar(self) -> str:
        """
        The URL of the avatar of the player's associated user.
        """
        return self.user.avatar.url

    @property
    def display_avatar(self) -> str:
        """
        The URL of the server avatar of the player's associated user. Equivalent to :attr:`avatar` if no server
        avatar exists.
        """
        return self.user.display_avatar.url

    @validate_arguments
    def pronoun(self, pronoun: Pronoun) -> str:
        if pronoun is Pronoun.THEIR:
            return {
                PronounType.MASCULINE: "his",
                PronounType.FEMININE: "her",
                PronounType.NEUTER: "its",
                PronounType.GENDER_NEUTRAL: "their",
            }[self.pronouns]

        genderinator = ifl.engine()
        genderinator.gender(self.pronouns.value)

        return genderinator.singular_noun(pronoun.value)

    # noinspection PyUnresolvedReferences
    async def _genderfabriken(self, *_) -> PronounType:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://pronoundb.org/api/v1/lookup",
                params={"platform": "discord", "id": self.id},
            ) as resp:
                pronoun_code = (
                    "tt" if resp.status != 200 else (await resp.json())["pronouns"]
                )

        with support.Assets.misc():
            type_codes = defaultdict(
                lambda: ["g", "g"], toml.load(open("pronouns.toml"))
            )[pronoun_code]

        return PronounType(random.choice(type_codes))

    def __str__(self):
        return self.name


class PlayerVoiceMixin:
    def voice_overwrites(self) -> discord.Permissions:
        """
        Return the voice channel permission overwrites for the player.
        """
        if self.game.host == self.user:
            overwrites = {
                "allow": discord.Permissions.voice() - discord.Permissions.stream,
                "deny": discord.Permissions.none(),
            }
        else:
            overwrites = {
                "allow": discord.Permissions(
                    connect=True, speak=True, use_voice_activation=True
                ),
                "deny": discord.Permissions.none(),
            }

        overwrites["allow"] += discord.Permissions(
            view_channel=True, read_message_history=True
        )

        return discord.PermissionOverwrite.from_pair(**overwrites)
