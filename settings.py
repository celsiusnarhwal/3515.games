"""
Production settings.
"""
import json
import os

import discord

# Dev Mode
DEV_MODE = False

# Owner ID
OWNER_ID = 170966436125212673

# Gateway Intents (https://discord.com/developers/docs/topics/gateway#gateway-intents)
INTENTS = discord.Intents.default()
INTENTS.members = True

# Debug Guilds
DEBUG_GUILDS = []

# Disabled Cogs
DISABLED_COGS = []

# Database Settings
DATABASE_SETTINGS = {"provider": "postgres", "dsn": os.getenv("DATABASE_URL")}

# Bot Token
TOKEN = os.getenv("DEV_TOKEN" if DEV_MODE else "BOT_TOKEN")

# local_settings.py, if present, will take precedence over settings.py
try:
    from local_settings import *
except ImportError:
    pass
