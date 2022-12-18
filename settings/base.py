########################################################################################################################
#                         Copyright (C) 2022-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
The base template for settings configurations. Settings configurations should:
- Import this template (from settings.base import *)
- Define ALL settings in this template with a value other than None
- Not define any settings that are not defined in this template
- Not import any names that are not imported in this template

If these rules are followed, 3515.games will refuse to start when undefined settings exist, significantly reducing
the possiblity that problems related to incorrectly-configured settings will arise whlile it is running.

Avoid running formatters that remove unused imports on this file (e.g. PyCharm's built-in formatter).
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
