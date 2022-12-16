########################################################################################################################
# Copyright (C) 2022 celsius narhwal
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of verion 3 of the GNU Affero General Public License as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
########################################################################################################################

"""
Bot events, setup functions, and the program entrypoint.
"""

import inspect
import logging
import subprocess

import alianator
import discord
import nltk
from rich.traceback import install
import cogs
import settings
import support
import uptime
from database.models import db

bot = discord.Bot(intents=settings.INTENTS, debug_guilds=settings.DEBUG_GUILDS, owner_id=settings.OWNER_ID)


# Bot Events

@bot.event
async def on_ready():
    """
    Prints a message to the console when 3515.games has connected to Discord and is ready for use.
    """
    print(f"{settings.BOT_NAME} is ready to play!", flush=True)
    await bot.register_commands(force=True)
    await bot.sync_commands(force=True)


@bot.event
async def on_guild_join(guild: discord.Guild):
    """
    Upon joining a server, sends an introduction message and checks whether 3515.games was added to the server with
    all the permissions it requested.

    :param guild: The server that was joined.
    """
    msg = "I'm **3515.games**, a bot that lets you play social games with your friends on Discord. " \
          "Thanks for inviting me!\n" \
          "\n" \
          "As long as I'm here, everyone in this server is subject to my Privacy Policy. " \
          "Give it a read at `/about` > Legal > Privacy Policy.\n\n"

    if guild.self_role.permissions < support.GamePermissions.everything():
        msg += "By the way, it looks like I wasn't added with all the permissions I need to function. " \
               "If I don't have all the permissions I need, some of my functionality may be limited or unavailable. " \
               "Use the 'Missing Permissions' button below to see which ones I still need.\n\n"

        if guild.owner.can_send(discord.Message):
            owner_msg = f"I'm **3515.games**, a bot that lets you enjoy social games with your friends on Discord.\n" \
                        f"\n" \
                        f"Sorry to bother you, but I was just added to your server, " \
                        f"[{guild.name}]({guild.jump_url}), and wasn't granted all of the permissions I need to " \
                        f"function. If I don't have all of the permissions I need, some of my functionality may " \
                        f"be limited or unavailable. For the best experience, please grant my integration's role, " \
                        f"**{guild.self_role.name}**, the following permissions in {guild.name}:\n\n"

            owner_msg += "\n".join(
                f"- {p}" for p in alianator.resolve(support.GamePermissions.everything() - guild.self_role.permissions)
            )

            owner_msg += "\n\nThanks!"

            embed = discord.Embed(title=f"Hey there, {guild.owner.name}! 👋🏾", description=owner_msg,
                                  color=support.Color.mint())

            await guild.owner.send(embed=embed)

    msg += "Let's have some fun together!"

    embed = discord.Embed(title="Hi there! 👋🏾", description=msg, color=support.Color.mint())

    if guild.system_channel.can_send(discord.Message):
        await guild.system_channel.send(embed=embed)


# Setup Functions


def print_copyright():
    """
    Prints 3515.games' copyright notice.
    """
    print(f"\n{open('COPYRIGHT').read()}\n\n")


def configure_logging():
    """
    Configures API event logging.
    """
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='3515.games.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)


def configure_cogs():
    """
    Initializes cogs.
    """
    all_cogs = set(
        cog[1] for cog in inspect.getmembers(cogs) if inspect.isclass(cog[1]) and issubclass(cog[1], cogs.MasterCog)
    )

    for cog in all_cogs.difference(settings.DISABLED_COGS):
        bot.add_cog(cog(bot=bot))


def configure_nltk():
    """
    Downloads NLTK corpora.
    """
    for corpus in settings.NLTK_CORPORA:
        nltk.download(corpus, quiet=True)


def configure_database():
    """
    Configures the database.
    """
    db.bind(**settings.DATABASE_SETTINGS)
    db.generate_mapping(create_tables=True)


def load_extensions():
    """
    Loads extensions.
    """
    bot.load_extensions(*settings.EXTENSIONS)


def start_api():
    """
    Starts the API.
    """
    subprocess.Popen(
        f"uvicorn api:app "
        f"--host {settings.API_HOST} "
        f"--port {settings.API_PORT} "
        f"--log-level {settings.API_LOG_LEVEL}",
        shell=True
    )


# Entrypoint

if __name__ == '__main__':
    settings.startup()
    print_copyright()
    configure_logging()
    configure_cogs()
    configure_nltk()
    configure_database()
    load_extensions()
    start_api()
    uptime.mark_startup()
    bot.run(settings.TOKE)
