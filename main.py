import inspect
import logging

import discord

import cogs
import settings
import uptime
from database.models import db

bot = discord.Bot(intents=settings.INTENTS, debug_guilds=settings.DEBUG_GUILDS)


@bot.event
async def on_ready():
    """
    Prints a message to the console when 3515.games has connected to Discord and is ready for use.
    """
    print(f"3515.games{'.dev' if settings.DEV_MODE else ''} is ready to play!", flush=True)
    await bot.register_commands(force=True)
    await bot.sync_commands(force=True)


def configure_logging():
    """
    Configures API event logging.
    """
    logger = logging.getLogger('discord')
    logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(filename='3515games.log', encoding='utf-8', mode='w')
    handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
    logger.addHandler(handler)


def cog_setup():
    """
    Initializes cogs.
    """
    all_cogs = [
        cog[1] for cog in inspect.getmembers(
            cogs, lambda obj: inspect.isclass(obj) and cogs.MasterCog in inspect.getmro(obj)[1:])
    ]

    for cog in all_cogs:
        if cog not in settings.DISABLED_COGS:
            bot.add_cog(cog(bot=bot))


def configure_database():
    """
    Configures the database.
    """
    db.bind(**settings.DATABASE_SETTINGS)
    db.generate_mapping(create_tables=True)


if __name__ == '__main__':
    configure_logging()
    configure_database()
    cog_setup()
    uptime.mark_startup()
    bot.run(settings.TOKEN)
