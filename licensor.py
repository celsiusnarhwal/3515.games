########################################################################################################################
#                         Copyright (C) 2022-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Generates the software license documentation hosted at https://3515.games/licenses.
"""

import json
import subprocess

import pyperclip

licenses = json.loads(
    subprocess.run("pip-licenses -f json --from=mixed --no-license-path --with-license-file", capture_output=True,
                   shell=True).stdout
)

fallbacks = {
    "Apache Software License": "https://opensource.org/licenses/Apache-2.0",
    "Apache License 2.0": "https://opensource.org/licenses/Apache-2.0",
    "BSD License": "https://opensource.org/licenses/BSD-3-Clause",
    "GNU General Public License": "https://opensource.org/licenses/gpl-license",
    "GNU Library or Lesser General Public License": "https://opensource.org/licenses/lgpl-license",
    "MIT License": "https://opensource.org/licenses/MIT",
    "Mozilla Public License 2.0": "https://opensource.org/licenses/MPL-2.0",
}

license_file = (
    "# Software Licenses\n\nThis page documents the licenses for the open source software used by 3515.games. "
    "The contents of this page are generated automatically and are not checked for accuracy, completeness, or "
    "consistency.\n\n<hr></hr>\n\n"
)

for lic in licenses:
    license_file += f"## {lic['Name']}\n### {lic['License']}\n\n"

    if lic["LicenseText"] != "UNKNOWN":
        license_file += f"{lic['LicenseText']}\n\n".replace("#", "").replace("=", "")
    else:
        for fallback in fallbacks:
            if fallback in lic["License"]:
                license_file += f"{lic['Name']} is licensed under the [{lic['License']}]({fallbacks[fallback]}).\n\n"

pyperclip.copy(license_file)
