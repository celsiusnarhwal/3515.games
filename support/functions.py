from __future__ import annotations

import discord
from discord import ButtonStyle
from discord.ext import pages, commands
from titlecase import titlecase

import support


# deocrators

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
            def resolve_name(permission_name: str) -> str:
                """
                Returns the user-facing aliases for permissions whose API names don't match up with their names
                in the Discord user interface.
                :param permission_name: The name of the permission.
                :return: The user-facing alias of the permission.
                """

                # the inlcusion of a permission in this dictionary does NOT necessarily mean it's used by the bot
                names = {
                    "external_emojis": "Use External Emoji",
                    "external_stickers": "Use External Stickers",
                    "manage_emojis": "Manage Emojis and Stickers",
                    "manage_guild": "Manage Server",
                    "mention_everyone": "Mention \\@everyone, \\@here, and All Roles",
                    "moderate_members": "Timeout Members",
                    "send_tts_messages": "Send Text-to-Speech Messages",
                    "start_embedded_activities": "Use Activities",
                    "stream": "Video",
                    "use_slash_commands": "Use Application Commands",
                    "use_voice_activation": "Use Voice Activity",
                }

                # simply removing the underscores and titlecasing the name will give us the user-facing alias in most
                # cases. the name resolution dictionary is only for when that doesn't work
                return names.get(permission_name) or titlecase(permission_name.replace("_", " "))

            # the missing permissions are represented by the intersection of the expected permissions and the
            # complement of the actual permissions (in english, it's the set of permissions that the bot both needs
            # and doesn't have)
            missing_permissions = discord.Permissions(expected_permissions.value & ~actual_permissions.value)

            message = f"I'm missing the following permissions that I need in order to use " \
                      f"`/{ctx.command.qualified_name}`: \n\n"

            message += "\n".join(
                [f"- {resolve_name(p[0])}" for p in missing_permissions if
                 p[1] is True]
            )

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


# non-decorators

def paginator_emoji_buttons(button_style: ButtonStyle = ButtonStyle.secondary):
    """
    Returns a list of emoji buttons for use with :class:`discord.ext.pages.Paginator`
    objects.

    :param button_style: The button style to use.
    """
    return [
        pages.PaginatorButton("first", emoji="⏮", style=button_style),
        pages.PaginatorButton("prev", emoji="⏪", style=button_style),
        pages.PaginatorButton("page_indicator", style=ButtonStyle.gray, disabled=True),
        pages.PaginatorButton("next", emoji="⏩", style=button_style),
        pages.PaginatorButton("last", emoji="⏭", style=button_style)
    ]


def posessive(string: str):
    """
    Returns a string with a possessive ending. Strings ending in "s" will be appended with a sole apostrophe; other
    strings will be appended with both an apostrophe and an "s".

    :param string: The string to append the possessive ending to.
    """
    return f"{string}'" if string.endswith('s') else f"{string}'s"
