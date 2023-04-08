########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import re
import subprocess


def get_poetry_version():
    version_pattern = re.compile(r"Poetry \(version (\d+\.\d+\.\d+)\)")

    return version_pattern.match(
        subprocess.run("poetry --version".split(), capture_output=True).stdout.decode()
    ).group(1)
