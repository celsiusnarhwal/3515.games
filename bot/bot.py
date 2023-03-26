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

import discord
import pendulum
from attrs import define
from click import secho as print

import support
from settings import settings


@define
class Bot(discord.Bot):
    intents: discord.Intents = settings.intents
    debug_guilds: list[int] = settings.debug_guilds
    owner_id: int = settings.owner_id

    def __attrs_pre_init__(self):
        super().__init__()

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


bot = Bot()


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
    Since the overwhelming majority of the bot's operations are catalyzed by application commands, this should
    be dispatched for most runtime exceptions. There's appparently nothing to be done about the ones it *isn't*
    dispatched for, though.
    """
    if type(exception) is not discord.CheckFailure:
        cause = exception.__cause__ or exception
        sys.excepthook(type(cause), cause, cause.__traceback__)


@bot.event
async def on_guild_join(guild: discord.Guild):
    """
    Sends a message upon joining a server.

    Parameters
    ----------
    guild : discord.Guild
        The server that was joined.
    """
    msg = (
        "I'm 3515.games. Thanks for inviting me!\n"
        "\n"
        "As long as I'm here, everyone in this server is subject to my "
        "[privacy policy](https://3515.games/legal/privacy).\n"
        "\n"
        "Let's have some fun! 🎉"
    )

    embed = discord.Embed(
        title="Hi there! 👋🏾", description=msg, color=support.Color.mint()
    ).set_footer(
        text=f"Copyright © {pendulum.now().year} celsius narhwal. Thank you kindly for your attention."
    )

    buttons = [
        discord.ui.Button(url="https://3515.games", emoji="🌐", label="www.3515.games"),
        discord.ui.Button(
            url="https://celsiusnarhwal.dev",
            emoji=discord.PartialEmoji.from_str("<:celsius:535601639235518465>"),
            label="celsiusnarhwal.dev",
        ),
    ]

    if guild.system_channel.can_send(discord.Message):
        await guild.system_channel.send(embed=embed, view=discord.ui.View(*buttons))


importlib.import_module("cogs")
