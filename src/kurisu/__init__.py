########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import os
import sys

from path import Path

here = Path(__file__).parent.realpath()
src = here.parent.realpath()
project = os.environ["PROJECT"] = src.parent.realpath()

for path in here, src:
    sys.path.insert(0, path)

src.chdir()
