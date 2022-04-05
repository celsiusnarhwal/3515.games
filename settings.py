import os

import discord
from dotenv import load_dotenv

load_dotenv()

# Debug Mode
DEBUG = False

# Gateway Intents
INTENTS = discord.Intents.default()
INTENTS.members = True

# Disabled Cogs
DISABLED_COGS = []

# Bot Token
TOKEN = os.getenv("BOT_TOKEN" if not DEBUG else "DEV_TOKEN")
