########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import os
import random
from functools import partial

import alianator
import clockworks
import discord
import tomlkit as toml
from dict_deep import deep_get
from discord import ButtonStyle
from discord.commands import application_command
from discord.ext import commands, pages
from github import Github as GitHub

import support
from gps import Routes
from support.models.commands import Pseudocommand

# constants

CELSIUSNARHWAL = 170966436125212673
CLESIUSNORHWALE = 417027940383981568

# decorators

slash_command = partial(discord.slash_command, guild_only=True)
pseudocommand = partial(application_command, cls=Pseudocommand)


def bot_has_permissions(expected_permissions: discord.Permissions):
    """
    A decorator that checks if the bot has a particular set of permissions at the channel level.

    :param expected_permissions: A discord.Permissions object representing the permissions to check for.
    the channel level.
    """

    async def predicate(ctx: discord.ApplicationContext):
        actual_permissions = ctx.channel.permissions_for(ctx.me)

        if actual_permissions < expected_permissions:
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

        return True

    return commands.check(predicate)


def invoked_in_text_channel():
    """
    A decorator that checks if a command was invoked invoked in a text channel.
    """

    async def predicate(ctx: discord.ApplicationContext):
        command_name = f"`/{ctx.command.qualified_name}`"
        if not isinstance(ctx.channel, discord.TextChannel):
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

        return True

    return commands.check(predicate)


def is_celsius_narhwal(user: discord.User = None):
    """
    A function that checks if a given user is 3515.games' owner.

    If the ``user`` parameter is not provided, this function will act as a command decorator and check against
    the invocation context.
    """

    async def predicate(ctx: discord.ApplicationContext):
        if not ctx.bot.is_owner(ctx.user):
            embed = discord.Embed(
                title="[EXTREMELY LOUD INCORRECT BUZZER]",
                description="You're not authorized to do that.",
                color=support.Color.error(),
            )
            await ctx.respond(embed=embed, ephemeral=True)

            return False

        return True

    return user.id == CELSIUSNARHWAL if user else commands.check(predicate)


def not_in_maintenance():
    """
    A decorator that checks if the bot is in maintenance mode.
    """

    async def predicate(ctx: discord.ApplicationContext):
        if clockworks.clock().maintenance_start_time is not None:
            maintenance_end_time = discord.utils.format_dt(
                clockworks.clock().maintenance_end_time, style="f"
            )

            msg = (
                "3515.games is currently in maintenance mode. You can't create new games while maintenance "
                "is in progress.\n"
                "\n"
                f"Maintenance is expected to end no later than "
                f"{maintenance_end_time} in your time zone."
            )

            embed = discord.Embed(
                title="Road work ahead.", description=msg, color=support.Color.orange()
            )
            await ctx.respond(embed=embed, ephemeral=True)

            return False

        return True

    return commands.check(predicate)


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


def split_list(seq: list, size: int) -> list[list]:
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


def zero_width_field() -> dict:
    """
    Return a dictionary of keyword arguments for creating a zero-width embed field.

    Examples
    --------
    >>> embed = discord.Embed()
    >>> embed.add_field(**zero_width_field())
    """
    return dict(name="\u200b", value="\u200b")


def version() -> str:
    """
    Return 3515.games' version.
    """
    with Routes.root():
        return deep_get(toml.load(open("pyproject.toml")), "tool.poetry.version")


def mona():
    """
    Return a PyGithub object for authenticated interactions with the GitHub API as @celsiusnarhwal.
    """
    gh = GitHub(os.getenv("GITHUB_TOKEN"))
    return gh.get_user("celsiusnarhwal")


def repo():
    """
    Return a PyGithub object for authenticated interactions with the celsiusnarhwal/3515.games GitHub repository.
    """
    return mona().get_repo("3515.games")
