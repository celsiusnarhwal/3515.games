"""
The base template for settings files. All other settings files must import the same modules and define the same
variables as this one (but should not import this file). This file exists largely to provide reference resolution and
code completion within my IDE and does not serve any runtime purpose.
"""

import os

import discord

import cogs

# Bot Name
BOT_NAME = None

# Application ID
APP_ID = None

# Owner ID (corresponds to celsiusnarhwal#3515)
OWNER_ID = None

# Gateway Intents (https://discord.com/developers/docs/topics/gateway#gateway-intents)
INTENTS = None

# Debug Guilds
DEBUG_GUILDS = None

# Extensions
EXTENSIONS = None

# Disabled Cogs
DISABLED_COGS = None

# NLTK Corpora (https://www.nltk.org/book/ch02)
NLTK_CORPORA = None

# Database Settings
DATABASE_SETTINGS = None

# API Settings
API_HOST = None
API_PORT = None
API_LOG_LEVEL = None

# Bot Token
TOKEN = None

# Startup Code
def startup():
    """
    Special startup code that only runs for this settings configuration.
    """
    pass