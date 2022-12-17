########################################################################################################################
#                         Copyright (C) 2022-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import urllib.parse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

import settings
from support import GamePermissions

app = FastAPI()

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"])


@app.get("/invite")
async def get_invite_url():
    """
    Dynamically generates and redirects to an invite link for 3515.games based on the permissions it requires as
    dictated by :class:`support.GamePermissions`.
    """
    base_url = "https://discord.com/api/oauth2/authorize"

    params = {
        "client_id": settings.APP_ID,
        "permissions": GamePermissions.everything().value,
        "scope": "bot applications.commands"
    }

    return RedirectResponse(f"{base_url}?{urllib.parse.urlencode(params)}")
