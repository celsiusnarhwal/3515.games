########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
The bot definition and event overrides.
"""

import importlib
import sys

import alianator
import discord
from click import secho as print

import support
from settings import settings


class Bot(discord.Bot):
    async def register_command(self, *args, **kwargs):
        await super().register_command(*args, **kwargs)

    def register_cog(self, cog: type):
        if cog not in settings.disabled_cogs:
            self.add_cog(cog(self))

        return cog

    @property
    def pending_application_commands(self):
        return [
            cmd
            for cmd in super().pending_application_commands
            if not isinstance(cmd, support.Pseudocommand)
        ]


bot = Bot(
    intents=settings.intents,
    debug_guilds=settings.debug_guilds,
    owner_id=settings.owner_id,
)


@bot.event
async def on_ready():
    """
    Prints a message to the console when 3515.games has connected to Discord and is ready for use.
    """
    print(f"{settings.bot_name} is ready to play! 🎉", fg="green")
    await bot.register_commands(force=True)
    await bot.sync_commands(force=True)


@bot.event
async def on_application_command_error(_, exception: discord.DiscordException):
    """
    Handles errors that occur during execution of application commands.

    Parameters
    ----------
    exception : discord.DiscordException
        The exception that was raised.

    Notes
    -----
    This overrides the default implemnetation of :meth:`discord.Bot.on_application_command_error`. Doing so allows
    for the suppression of :class:`discord.CheckFailure` exceptions, as it is generally not useful to know that one
    has been raised. In development, it also allows for the propagation of exception tracebacks to Rich.[1]_

    Since the overwhelming majority of the bot's operations are catalyzed by application commands, this should
    be dispatched for most runtime exceptions.

    References
    ----------
    .. [1] https://rich.readthedocs.io/en/latest/traceback.html
    """
    if type(exception) is not discord.CheckFailure:
        cause = exception.__cause__ or exception
        sys.excepthook(type(cause), cause, cause.__traceback__)


@bot.event
async def on_guild_join(guild: discord.Guild):
    """
    Upon joining a server, sends an introduction message and checks whether 3515.games was added to the server with
    all the permissions it requested.

    Parameters
    ----------
    guild : discord.Guild
        The server that was joined.
    """
    msg = (
        "I'm **3515.games**, a bot that lets you play social games with your friends on Discord. "
        "Thanks for inviting me!\n"
        "\n"
        "As long as I'm here, everyone in this server is subject to my Privacy Policy. "
        "Give it a read at `/about` > Legal > Privacy Policy.\n\n"
    )

    if guild.self_role.permissions < support.GamePermissions.everything():
        msg += (
            "By the way, it looks like I wasn't added with all the permissions I need to function. "
            "If I don't have all the permissions I need, some of my functionality may be limited or unavailable. "
            "Use the 'Missing Permissions' button below to see which ones I still need.\n\n"
        )

        if guild.owner.can_send(discord.Message):
            owner_msg = (
                f"I'm **3515.games**, a bot that lets you enjoy social games with your friends on Discord.\n"
                f"\n"
                f"Sorry to bother you, but I was just added to your server, "
                f"[{guild.name}]({guild.jump_url}), and wasn't granted all of the permissions I need to "
                f"function. If I don't have all of the permissions I need, some of my functionality may "
                f"be limited or unavailable. For the best experience, please grant my integration's role, "
                f"**{guild.self_role.name}**, the following permissions in {guild.name}:\n\n"
            )

            owner_msg += "\n".join(
                f"- {p}"
                for p in alianator.resolve(
                    support.GamePermissions.everything() - guild.self_role.permissions
                )
            )

            owner_msg += "\n\nThanks!"

            embed = discord.Embed(
                title=f"Hey there, {guild.owner.name}! 👋🏾",
                description=owner_msg,
                color=support.Color.mint(),
            )

            await guild.owner.send(embed=embed)

    msg += "Let's have some fun together!"

    embed = discord.Embed(
        title="Hi there! 👋🏾", description=msg, color=support.Color.mint()
    )

    if guild.system_channel.can_send(discord.Message):
        await guild.system_channel.send(embed=embed)


importlib.import_module("cogs")
