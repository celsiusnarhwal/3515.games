########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import inspect
import sys

from cogs.cah.cog import CAHCog
from cogs.chess.cog import ChessCog
from cogs.generic import *
from cogs.rps.cog import RPSCog
from cogs.uno.cog import UnoCog

all_cogs = {
    cog
    for _, cog in inspect.getmembers(sys.modules[__name__], inspect.isclass)
    if issubclass(cog, MasterCog)
}
