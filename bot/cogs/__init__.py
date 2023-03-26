########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import importlib

from cogs.base import Cog
from path import Path

# my day be so fine and then BOOM! circular import
for pkg in [d for d in Path(__file__).parent.dirs() if (d / "__init__.py").exists()]:
    importlib.import_module(f"cogs.{pkg.stem}.cog")
