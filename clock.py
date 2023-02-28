########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Timekeeping for uptime and maintenance.
"""

from __future__ import annotations

import pendulum
from attrs import define

from support import Fields

__all__ = ["start", "clock"]

clockworks: Clock = None


@define
class Clock:
    startup_time: pendulum.DateTime = Fields.attr(factory=pendulum.now)
    maintenance_start: pendulum.DateTime = Fields.attr(default=None)

    def start_maintenance(self):
        """
        Enter maintenance mode.

        Maintenance mode disables the creation of new games while 3515.games is preparing for a new release.

        Warnings
        --------
        Maintenance mode, once entered, is permanent for the current session, reversible only by restarting the bot.
        """
        self.maintenance_start = pendulum.now()

    @property
    def uptime(self) -> int:
        """
        The bot's uptime in seconds.
        """
        return (pendulum.now() - self.startup_time).seconds

    @property
    def maintenance_end(self) -> pendulum.DateTime:
        """
        The projected end time of the current maintenance period.
        """
        if not self.maintenance_start:
            raise RuntimeError("3515.games is not in maintenance mode.")

        return self.maintenance_start + pendulum.duration(hours=8)


def start():
    """
    Start the clock.
    """
    global clockworks
    clockworks = Clock()


def clock() -> Clock:
    """
    Return the clock.
    """
    if not clockworks:
        raise RuntimeError(
            "The clock has not been started. You may need to call start()."
        )

    return clockworks
