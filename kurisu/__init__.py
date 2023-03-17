########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import sys

from path import Path

here = Path(__file__).parent
bot = here.parent / "bot"

for path in [here, bot]:
    sys.path.append(str(path))
