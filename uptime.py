########################################################################################################################
#                         Copyright (C) 2022-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Tracks uptime.
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
