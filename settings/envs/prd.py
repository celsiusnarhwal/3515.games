########################################################################################################################
#                         Copyright (C) 2022-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Production settings.
"""

import os

import discord

import cogs

# Bot Name
BOT_NAME = "3515.games"

# Application ID
APP_ID = 939972078323519488

# Owner ID (corresponds to celsiusnarhwal#3515)
OWNER_ID = 170966436125212673

# Gateway Intents (https://discord.com/developers/docs/topics/gateway#gateway-intents)
INTENTS = discord.Intents.default() + discord.Intents.members

# Debug Guilds
DEBUG_GUILDS = []

# Extensions
EXTENSIONS = []

# Disabled Cogs
DISABLED_COGS = [cogs.GeneriCog]

# NLTK Corpora (https://www.nltk.org/book/ch02)
NLTK_CORPORA = ["averaged_perceptron_tagger"]

# Database Settings
DATABASE_SETTINGS = {
    "provider": "postgres",
    "dsn": os.getenv("DATABASE_URL")
}

# API Settings
API_HOST = "0.0.0.0"
API_PORT = os.getenv("PORT")
API_LOG_LEVEL = "critical"

# Bot Token
TOKEN = os.getenv("BOT_TOKEN")
