# 3515.games is source-available, not open source. You may not use, modify, or redistribute 3515.games' source code
# without the express written permission of celsius narhwal.

# 3515.games © celsius narhwal. All rights reserved.

import inspect
import logging

import discord

import cogs
import settings

bot = discord.Bot(intents=settings.INTENTS)


@bot.event
async def on_ready():
    """
    Prints a message to the console when 3515.games has connected to Discord and is ready for use.
    """
    print(f"3515.games{'.dev' if settings.DEV_MODE else ''} is ready to play!")
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


if __name__ == '__main__':
    configure_logging()
    cog_setup()
    bot.run(settings.TOKEN)
