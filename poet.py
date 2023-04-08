########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Maintains a consistent Poetry version in Docker containers and CI systems.
"""

import tomllib

print(tomllib.load(open("pyproject.toml", "rb"))["extra"]["poetry-version"])
