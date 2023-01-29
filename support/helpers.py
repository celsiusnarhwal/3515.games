########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import os
import random

import alianator
import discord
import tomlkit as toml
from discord import ButtonStyle
from discord.commands import application_command
from discord.ext import pages, commands
from github import Github as GitHub, AuthenticatedUser, Repository
from tomlkit import TOMLDocument

import support


# decorators


def slash_command(**attrs):
    """
    Equivalent to :meth:`discord.slash_command` with the exception that commands created with this decorator
    are always guild-only.

    All arguments accepted by :meth:`discord.slash_command` are accepted by this decorator.

    Notes
    -----
    All of 3515.games' commands are guild-only. Using this decorator is preferred to explicitly passing
    `guild_only=True` to every invocation of :meth:`discord.commands.slash_command`.
    """
    return discord.slash_command(guild_only=True, **attrs)


def pseudocommand():
    """
    A decorator that creates a pseudocommand.

    Examples
    --------
    >>> import support
    ... @support.pseudocommand()
    ... async def command(ctx):
    ...     ...

    See Also
    --------
    :class:`support.models.PseudoCommand`
    """
    return application_command(cls=support.Pseudocommand)


def bot_has_permissions(expected_permissions: discord.Permissions):
    """
    A decorator that checks if the bot has a particular set of permissions at the channel level.

    :param expected_permissions: A discord.Permissions object representing the permissions to check for.
    the channel level.
    """

    async def predicate(ctx: discord.ApplicationContext):
        actual_permissions = ctx.channel.permissions_for(ctx.me)

        if actual_permissions >= expected_permissions:
            return True
        else:
            message = (
                f"I'm missing the following permissions that I need in order to use "
                f"`/{ctx.command.qualified_name}` in this channel: \n\n"
            )

            message += "\n".join(
                f"- {p}"
                for p in alianator.resolve(expected_permissions - actual_permissions)
            )

            message += "\n\n Once I've been given those permissions, try again."

            embed = discord.Embed(
                title="I need more power!",
                description=message,
                color=support.Color.error(),
            )

            await ctx.respond(embed=embed, ephemeral=True)

            return False

    return commands.check(predicate)


def invoked_in_text_channel():
    """
    A decorator that checks if a command was invoked invoked in a text channel.
    """

    async def predicate(ctx: discord.ApplicationContext):
        command_name = f"`/{ctx.command.qualified_name}`"
        if isinstance(ctx.channel, discord.TextChannel):
            return True
        else:
            message = (
                f"You can only use {command_name} in regular text channels - not threads. "
                f"Go to a text channel, then try again."
            )
            embed = discord.Embed(
                title="You can't do that in a thread.",
                description=message,
                color=support.Color.error(),
            )

            await ctx.respond(embed=embed, ephemeral=True)
            return False

    return commands.check(predicate)


def is_celsius_narhwal(user: discord.User = None):
    """
    A function that checks if a given user is 3515.games' owner, celsiusnarhwal#3515.

    If the ``user`` parameter is not provided, this function will act as a command decorator and check against
    the invocation context.
    """

    async def predicate(ctx: discord.ApplicationContext):
        if ctx.bot.is_owner(ctx.user):
            return True
        else:
            msg = f"Only my creator can use `/{ctx.command.qualified_name}`."
            embed = discord.Embed(
                title="You can't do that.", description=msg, color=support.Color.error()
            )
            await ctx.respond(embed=embed, ephemeral=True)

            return False

    return user.id == 170966436125212673 if user else commands.check(predicate)


# miscellaneous


def pagimoji(
    button_style: ButtonStyle = ButtonStyle.secondary,
) -> list[pages.PaginatorButton]:
    """
    Returns a list of emoji buttons for use with :class:`discord.ext.pages.Paginator`
    objects.

    :param button_style: The button style to use.
    """
    return [
        pages.PaginatorButton("first", label="", emoji="⏮", style=button_style),
        pages.PaginatorButton("prev", label="", emoji="⏪", style=button_style),
        pages.PaginatorButton(
            "page_indicator", label="", style=ButtonStyle.gray, disabled=True
        ),
        pages.PaginatorButton("next", label="", emoji="⏩", style=button_style),
        pages.PaginatorButton("last", label="", emoji="⏭", style=button_style),
    ]


def split_list(seq: list, size: int) -> list:
    """
    Split a list into smaller lists of the specified size.

    :param seq: The list to split.
    :param size: The size of each sublist.
    """
    return [seq[i : i + size] for i in range(0, len(seq), size)]


def fuzz(num: int | float) -> float:
    """
    Fuzz a number to a value slightly higher or lower than its original.

    Parameters
    ----------
    num : int | float
        The number to fuzz.

    Returns
    -------
    float
        The fuzzed number.
    """
    return num + (num * 0.1 * (0.5 - random.random()))


def pyproject() -> TOMLDocument:
    """
    Return a dictionary-like object representing 3515.games pyproject.toml file.
    """
    return toml.load(open("pyproject.toml"))["tool"]["poetry"]


def github() -> AuthenticatedUser:
    gh = GitHub(os.getenv("GITHUB_TOKEN"))
    return gh.get_user("celsiusnarhwal")


def bot_repo() -> Repository:
    return github().get_repo("3515.games")
