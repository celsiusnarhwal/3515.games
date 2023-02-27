########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Tracks uptime.
"""

import humanize
import pendulum

startup_time = None


def mark_startup():
    """
    Record the time at which the bot started.
    """
    global startup_time
    startup_time = pendulum.now()


def get_uptime() -> str:
    """
    Return a string representation of the bot's uptime.
    """
    if not startup_time:
        raise RuntimeError(
            "Startup time has not been recorded. You may need to call mark_startup()."
        )

    return humanize.naturaldelta(pendulum.now() - startup_time)
