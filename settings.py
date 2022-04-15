"""
Production settings.
"""

import os

import discord

import cogs

# Dev Mode
DEV_MODE = False

# Gateway Intents (https://discord.com/developers/docs/topics/gateway#gateway-intents)
INTENTS = discord.Intents.default()
INTENTS.members = True

# Debug Guilds
DEBUG_GUILDS = []

# Disabled Cogs
DISABLED_COGS = [cogs.ChessCog]

# Bot Token
TOKEN = os.getenv("DEV_TOKEN" if DEV_MODE else "BOT_TOKEN")

# local_settings.py, if present, will take precedence over settings.py
try:
    from local_settings import *
except ImportError:
    pass
