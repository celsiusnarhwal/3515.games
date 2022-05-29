"""
Production settings.
"""
import json
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

# Database Settings
DATABASE_SETTINGS = {"provider": "postgres", "host": "app-a51d941a-5b14-4af2-ba67-aab04e4d0dd3-do-user-11351003-0.b.db.ondigitalocean.com", "port": 25060, "user": "db3515", "password": "AVNS_3ANYqsUnoWTs2iL", "database": "db3515", "sslmode": "require"}

# Bot Token
TOKEN = os.getenv("DEV_TOKEN" if DEV_MODE else "BOT_TOKEN")

# local_settings.py, if present, will take precedence over settings.py
try:
    from local_settings import *
except ImportError:
    pass
