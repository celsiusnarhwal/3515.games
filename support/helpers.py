from __future__ import annotations

import os

import alianator
import discord
from discord import ButtonStyle
from discord.ext import pages, commands
from github import Github as GitHub

import support


# decorators

def is_celsius_narhwal(user: discord.User = None):
    """
    A function that checks if a given user is celsiusnarhwal#3515.

    If the ``user`` parameter is not provided, this function will act as a command decorator and check against
    the invocation context.
    """
    celsius_id = 170966436125212673

    async def predicate(ctx: discord.ApplicationContext):
        if ctx.user.id == celsius_id:
            return True
        else:
            msg = f"Only my creator can use `/{ctx.command.qualified_name}`."
            embed = discord.Embed(title="You can't do that.", description=msg, color=support.Color.red())
            await ctx.respond(embed=embed, ephemeral=True)

            return False

    return user.id == celsius_id if user else commands.check(predicate)


def bot_has_permissions(expected_permissions):
    """
    A decorator that checks if the bot has a particular set of permissions.

    :param expected_permissions: A ``discord.Permissions`` object representing the permissions to check for.
    """

    async def predicate(ctx):

        actual_permissions = ctx.channel.permissions_for(ctx.me)

        # the actual permissions granted to the bot must be a superset of (i.e. greater than or equal to) the expected
        # permissions
        if actual_permissions.is_superset(expected_permissions):
            return True
        else:
            # the missing permissions are represented by the intersection of the expected permissions and the
            # complement of the actual permissions (in english, it's the set of permissions that the bot both needs
            # and doesn't have)
            missing_permissions = discord.Permissions(expected_permissions.value & ~actual_permissions.value)

            message = f"I'm missing the following permissions that I need in order to use " \
                      f"`/{ctx.command.qualified_name}` in this channel: \n\n"

            message += "\n".join(f"- {p}" for p in alianator.resolve(missing_permissions))

            message += "\n\n Once I've been given those permissions, try again."

            embed = discord.Embed(title="I need more power!", description=message, color=support.Color.red())

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
            message = f"You can only use {command_name} in regular text channels - not threads. " \
                      f"Go to a text channel, then try again."
            embed = discord.Embed(title="You can't do that in a thread.", description=message,
                                  color=support.Color.red())

            await ctx.respond(embed=embed, ephemeral=True)
            return False

    return commands.check(predicate)


# miscellaneous

def paginator_emoji_buttons(button_style: ButtonStyle = ButtonStyle.secondary) -> list[pages.PaginatorButton]:
    """
    Returns a list of emoji buttons for use with :class:`discord.ext.pages.Paginator`
    objects.

    :param button_style: The button style to use.
    """
    return [
        pages.PaginatorButton("first", label="", emoji="⏮", style=button_style),
        pages.PaginatorButton("prev", label="", emoji="⏪", style=button_style),
        pages.PaginatorButton("page_indicator", label="", style=ButtonStyle.gray, disabled=True),
        pages.PaginatorButton("next", label="", emoji="⏩", style=button_style),
        pages.PaginatorButton("last", label="", emoji="⏭", style=button_style)
    ]


def posessive(string: str) -> str:
    """
    Returns a string with a possessive ending. Strings ending in "s" will be appended with a sole apostrophe; other
    strings will be appended with both an apostrophe and an "s".

    :param string: The string to append the possessive ending to.
    """
    return f"{string}'" if string.endswith("s") else f"{string}'s"


def split_list(seq: list, size: int) -> list:
    """
    Splits a list into smaller lists of the specified size.

    :param seq: The list to split.
    :param size: The size of each sublist.
    """
    return [seq[i:i + size] for i in range(0, len(seq), size)]


def get_repo():
    gh = GitHub(os.getenv("GITHUB_TOKEN"))
    return gh.get_repo("celsiusnarhwal/3515.games")