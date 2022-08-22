import os
import urllib.parse

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer

import settings
from support import GamePermissions

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def api_key_auth(api_key: str = Depends(oauth2_scheme)):
    if api_key != os.getenv("BOT_API_KEY"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Forbidden")


app = FastAPI()

app.add_middleware(CORSMiddleware,
                   allow_origins=["*"],
                   allow_credentials=True,
                   allow_methods=["*"],
                   allow_headers=["*"])


@app.get("/invite")
async def get_invite_url():
    base_url = "https://discord.com/api/oauth2/authorize"

    params = {
        "client_id": settings.APP_ID,
        "permissions": GamePermissions.everything().value,
        "scope": "bot applications.commands"
    }

    return RedirectResponse(f"{base_url}?{urllib.parse.urlencode(params)}")
