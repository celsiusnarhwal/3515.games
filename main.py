"""
3515.games' execution point. Running this script starts up the bot.
"""

import logging
import os

import discord

import cogs

intents = discord.Intents.default()

# noinspection PyDunderSlots,PyUnresolvedReferences
intents.members = True

bot = discord.Bot(debug_guilds=[392426193581768717, 941766354380394506, 941816746162159636],
                  intents=intents)


@bot.event
async def on_ready():
    """
    Prints a message to the console when 3515.games has connected to Discord and is ready for use.
    """
    print("3515.games is ready to play!")
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
    all_cogs = [cogs.RockPaperScissorsCog, cogs.AboutCog, cogs.UnoCog]
    for cog in all_cogs:
        bot.add_cog(cog(bot=bot))


if __name__ == '__main__':
    configure_logging()
    cog_setup()
    bot.run(os.getenv("BOT_TOKEN"))
