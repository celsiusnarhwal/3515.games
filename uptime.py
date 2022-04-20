"""
A small module whose dedicated purpose is to track the bot's uptime.
"""

from datetime import datetime
import humanize

startup_time = None


def mark_startup():
    global startup_time
    startup_time = datetime.now()


def get_uptime():
    if startup_time:
        return humanize.naturaldelta(datetime.now() - startup_time)
