########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Bot events, setup functions, and the program main.
"""

import inspect
import logging
import warnings

import alianator
import discord
import nltk
from click import secho as print

import cogs
import support
import uptime
from database.models import db
from settings import settings

bot = discord.Bot(
    intents=settings.intents,
    debug_guilds=settings.debug_guilds,
    owner_id=settings.owner_id,
)


# Bot Events


@bot.event
async def on_ready():
    """
    Prints a message to the console when 3515.games has connected to Discord and is ready for use.
    """
    print(f"{settings.bot_name} is ready to play! 🎉", fg="green")
    await bot.register_commands(force=True)
    await bot.sync_commands(force=True)


@bot.event
async def on_application_command_error(
    ctx: discord.ApplicationContext, exception: discord.DiscordException
):
    """
    Handles errors that occur during execution of application commands.

    Parameters
    ----------
    ctx : discord.ApplicationContext
        The command context.
    exception : discord.DiscordException
        The exception that was raised.
    """
    try:
        raise exception
    except discord.CheckFailure:
        pass
    except discord.DiscordException:
        settings.tracer()


@bot.event
async def on_guild_join(guild: discord.Guild):
    """
    Upon joining a server, sends an introduction message and checks whether 3515.games was added to the server with
    all the permissions it requested.

    :param guild: The server that was joined.
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


# Setup Functions


def configure_logging():
    """
    Configures API event logging.
    """
    logger = logging.getLogger("discord")
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename="3515.games.log", encoding="utf-8", mode="w")
    handler.setFormatter(
        logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
    )
    logger.addHandler(handler)


def suppress_warnings():
    """
    Suppresss warnings as indicated by the bot's settings.
    """
    for warning in settings.suppressed_warnings:
        warnings.filterwarnings("ignore", category=warning)


def configure_cogs():
    """
    Initializes cogs.
    """
    all_cogs = set(
        cog
        for _, cog in inspect.getmembers(cogs)
        if inspect.isclass(cog) and issubclass(cog, cogs.MasterCog)
    )

    for cog in all_cogs.difference(settings.disabled_cogs):
        bot.add_cog(cog(bot))


def configure_nltk():
    """
    Downloads NLTK corpora.
    """
    for corpus in settings.nltk_corpora:
        nltk.download(corpus, quiet=True)


def configure_database():
    """
    Configures the database.
    """
    db.bind(**settings.database)
    db.generate_mapping(create_tables=True)


def load_extensions():
    """
    Loads extensions.
    """
    bot.load_extensions(*settings.extensions)


def setup():
    """
    Calls the previous functions.
    """
    configure_logging()
    suppress_warnings()
    configure_cogs()
    configure_nltk()
    configure_database()
    load_extensions()


# Entrypoint

if __name__ == "__main__":
    print(f"\n{open('COPYING').read()}\n", fg="magenta")

    print(f"Hello! {settings.bot_name} will be ready in just a moment.")

    setup()

    uptime.mark_startup()
    bot.run(settings.token)
