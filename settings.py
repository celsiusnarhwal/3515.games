"""
Production settings.
"""
import os

import discord

import cogs

# Dev Mode
DEV_MODE = False

# Bot Name
BOT_NAME = "3515.games"

# Owner ID (corresponds to celsiusnarhwal#3515)
OWNER_ID = 170966436125212673

# Gateway Intents (https://discord.com/developers/docs/topics/gateway#gateway-intents)
INTENTS = discord.Intents.default() + discord.Intents.members

# Debug Guilds
DEBUG_GUILDS = []

# Extensions
EXTENSIONS = ["jishaku"]

# Disabled Cogs
DISABLED_COGS = [cogs.AboutCog]

# NLTK Corpora (https://www.nltk.org/book/ch02)
NLTK_CORPORA = ["averaged_perceptron_tagger"]

# Database Settings
DATABASE_SETTINGS = {"provider": "postgres", "dsn": os.getenv("DATABASE_URL")}

# Bot Token
TOKEN = os.getenv("BOT_TOKEN" if not DEV_MODE else "DEV_TOKEN")

# local_settings.py, if it exists, will override the values defined above
try:
    from local_settings import *
except ImportError:
    pass
