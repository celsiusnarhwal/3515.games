########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

from __future__ import annotations

import pendulum
from attrs import define

from support import Fields

__all__ = ["start_clock", "clock"]

_clock: Clock = None


@define
class Clock:
    startup_time: pendulum.DateTime = Fields.attr(factory=pendulum.now)
    maintenance_start_time: pendulum.DateTime = Fields.attr(default=None)

    def start_maintenance(self):
        """
        Enter maintenance mode.

        Maintenance mode disables the creation of new games while 3515.games is preparing for a new release.

        Warnings
        --------
        Maintenance mode, once entered, is permanent for the current session, reversible only by restarting the bot.
        """
        self.maintenance_start_time = pendulum.now()

    @property
    def uptime(self) -> int:
        """
        The bot's uptime in seconds.
        """
        return (pendulum.now() - self.startup_time).seconds

    @property
    def maintenance_end_time(self) -> pendulum.DateTime:
        """
        The projected end time of the current maintenance period.
        """
        if not self.maintenance_start_time:
            raise RuntimeError("3515.games is not in maintenance mode.")

        return self.maintenance_start_time + pendulum.duration(hours=8)


def start_clock():
    """
    Start the clock.
    """
    global _clock
    _clock = Clock()


def clock() -> Clock:
    """
    Return the clock.
    """
    if not _clock:
        raise RuntimeError(
            "The clock has not been started. You may need to start_clock()."
        )

    return _clock
