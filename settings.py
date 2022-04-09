"""
Production settings.
"""

# Don't change these settings unless there's a *very* good reason to. To override these settings in a development
# environment, use local_settings.py, or create it if it doesn't exist.

import os

import discord

# Dev Mode
DEV_MODE = False

# Gateway Intents (https://discord.com/developers/docs/topics/gateway#gateway-intents)
INTENTS = discord.Intents.default()
INTENTS.members = True

# Debug Guilds
DEBUG_GUILDS = []

# Disabled Cogs
DISABLED_COGS = []

# Bot Token
TOKEN = os.getenv("DEV_TOKEN" if DEV_MODE else "BOT_TOKEN")

# local_settings.py, if present, will take precedence over settings.py
try:
    from local_settings import *
except ImportError:
    pass
