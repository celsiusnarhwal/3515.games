"""
Kurisu, 3515.games' development CLI, provides command-line shortcuts for common development tasks.
"""

import importlib
import os
import sys
import urllib.parse
from enum import Enum

import pyperclip
import typer
from path import Path

import kurisu.settings
import support
from settings import settings

here = Path(__file__).parent
root = here.parent

app = typer.Typer(pretty_exceptions_show_locals=False)

app.add_typer(kurisu.settings.app, name="settings")


class ExitPortal(str, Enum):
    home = "home"
    docs = "docs"
    app = "app"


@app.command(name="copyright")
def copyright():
    """
    Attach copyright notices to all Python source files.
    """


@app.command(name="licenses")
def licenses():
    """
    Get Markdown-formatted documentation of 3515.games' software licenses.
    """


@app.command(name="invite")
def invite(production: bool = typer.Option(None, "--production", "-p",
                                           help="Generate an invite link for the "
                                                "production instance of 3515.games."),
           copy: bool = typer.Option(None, "--copy", "-c", help="Copy the invite link to the clipboard."),
           launch: bool = typer.Option(None, "--open", "-o", help="Open the invite link in a web browser.")):
    """
    Generate an invite link for 3515.games. By default, this generates an invite link for the development instance.
    """
    if production:
        os.environ["DOPPLER_ENVIRONMENT"] = os.environ["DOPPLER_CONFIG"] = "prd"
        importlib.reload(sys.modules["settings"])

    from settings import settings

    base_url = "https://discord.com/api/oauth2/authorize"

    params = {
        "client_id": settings.app_id,
        "permissions": support.GamePermissions.everything().value,
        "scope": "bot applications.commands",
    }

    invite_url = f"{base_url}?{urllib.parse.urlencode(params)}"

    if not (copy or launch):
        print(invite_url)
    else:
        if copy:
            pyperclip.copy(invite_url)
        if launch:
            typer.launch(invite_url)


@app.command(name="portal")
def portal(destination: ExitPortal = typer.Argument("home",
                                                    help="Where on the developer portal to go. Choose from "
                                                         "home (the home page), docs (the documentation), or "
                                                         "app (3515.games.dev's application page).")):
    """
    Open the Discord Developer Portal.
    """
    portals = {
        "home": "https://discord.com/developers/",
        "docs": "https://discord.com/developers/docs/",
        "app": f"https://discord.com/developers/applications/{settings.app_id}/information/",
    }

    typer.launch(portals[destination])


@app.callback()
def main():
    """
    Kurisu is 3515.games' development command-line interface.
    """


if __name__ == '__main__':
    # Only use when developing Kurisu itself. Otherwise, use the `kurisu` command.
    app()
