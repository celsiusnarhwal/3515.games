"""
Development settings.
"""

import os

import discord

import cogs

# Bot Name
BOT_NAME = "3515.games.dev"

# Application ID
APP_ID = 960228863986761778

# Owner ID (corresponds to celsiusnarhwal#3515)
OWNER_ID = 170966436125212673

# Gateway Intents (https://discord.com/developers/docs/topics/gateway#gateway-intents)
INTENTS = discord.Intents.default() + discord.Intents.members

# Debug Guilds
DEBUG_GUILDS = []

# Extensions
EXTENSIONS = []

# Disabled Cogs
DISABLED_COGS = []

# NLTK Corpora (https://www.nltk.org/book/ch02)
NLTK_CORPORA = ["averaged_perceptron_tagger"]

# Database Settings
DATABASE_SETTINGS = {
    "provider": "sqlite",
    "filename": "db.sqlite",
    "create_db": True,
}

# API Settings
API_HOST = "127.0.0.1"
API_PORT = 8080
API_LOG_LEVEL = "info"

# Bot Token
TOKEN = os.getenv("BOT_TOKEN")
