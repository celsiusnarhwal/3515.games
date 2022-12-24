########################################################################################################################
#                         Copyright (C) 2022-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Kurisu, 3515.games' development CLI, provides command-line shortcuts for common development tasks.
"""

import importlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.parse
from enum import Enum

import gitignorefile as gitignore
import inflect as ifl
import pyperclip
import typer
from path import Path
from rich import print

import kurisu.settings
import support
from settings import settings

inflect = ifl.engine()

here = Path(__file__).parent
root = here.parent

app = typer.Typer(pretty_exceptions_show_locals=False)
app.add_typer(kurisu.settings.app, name="settings")


@app.command(name="copyright")
def copyright(verbose: bool = typer.Option(None, "--verbose", "-v", help="Show the name of each changed file."),
              quiet: bool = typer.Option(None, "--quiet", "-q",
                                         help="Suppress all output aside from errors. Overrides -v."),
              dry_run: bool = typer.Option(None, "--dry-run", "-n", help="Run as usual but without actually "
                                                                         "changing any files.")):
    """
    Attach copyright notices to all non-gitignored Python source files.
    """

    def echo(*args, **kwargs):
        if not quiet:
            print(*args, **kwargs)

    verbose = verbose and not quiet

    notice = Path(here / "templates" / "static" / "copyright.txt").read_text().strip("\n") + "\n\n"
    is_ignored = gitignore.parse(root / ".gitignore")
    changed = 0

    for file in root.walkfiles("*.py"):
        if notice not in file.text() and not is_ignored(file):
            changed += 1

            if verbose:
                echo(f"[bold yellow]Changed[/]: {file}")

            if not dry_run:
                file.write_text(notice + file.text())

    if changed:
        output = f"[green]Changed [bold]{changed}[/bold] {inflect.plural('file', changed)}"
    else:
        output = "[green] No files changed"

    if dry_run:
        output += " (dry run)"

    echo(output)


@app.command(name="licenses")
def licenses(output: pathlib.Path = typer.Option(None, "--output", "-o",
                                                 help="The file to write licenses to. If neither this "
                                                      "nor -c are provided, the licenses will be "
                                                      "printed to standard output."),
             copy: bool = typer.Option(None, "--copy", "-c", help="Copy the licenses to the clipboard. If neither "
                                                                  "this nor -o are provided, the licenses will be "
                                                                  "printed to standard output")):
    """
    Create Markdown-formatted documentation of 3515.games' software licenses.
    """
    documents = json.loads(
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

    for doc in documents:
        if doc["Name"] != "3515-games":
            license_file += f"## {doc['Name']}\n### {doc['License']}\n\n"

            if doc["LicenseText"] != "UNKNOWN":
                license_file += f"{doc['LicenseText']}\n\n".replace("#", "").replace("=", "")
            else:
                for fallback in fallbacks:
                    if fallback in doc["License"]:
                        license_file += (f"{doc['Name']} is licensed under the "
                                         f"[{doc['License']}]({fallbacks[fallback]}).\n\n")

    if not (output or copy):
        print(license_file)
    else:
        if output:
            output.write_text(license_file)

        if copy:
            pyperclip.copy(license_file)


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

    # this needs to be re-imported locally after importlib.reload is called
    from settings import settings

    base_url = "https://discord.com/api/oauth2/authorize"

    params = {
        "client_id": settings.app_id,
        "permissions": support.GamePermissions.everything().value,
        "scope": "bot applications.commands",
    }

    invite_url = f"{base_url}?{urllib.parse.urlencode(params)}"
    print(invite_url)

    if copy:
        pyperclip.copy(invite_url)
    if launch:
        typer.launch(invite_url)


class PortalGate(str, Enum):
    home = "home"
    docs = "docs"
    app = "app"


@app.command(name="portal")
def portal(gate: PortalGate = typer.Argument(PortalGate.home, show_default="home",
                                             help="Where on the developer portal to go. Choose from "
                                                  "home (the home page), docs (the documentation), or "
                                                  "app (3515.games.dev's application page).")):
    """
    Open the Discord Developer Portal.
    """
    blue = "https://discord.com/developers"

    orange = {
        "home": "/",
        "docs": "/docs",
        "app": f"/applications/{settings.app_id}/information/",
    }

    typer.launch(blue + orange[gate])


@app.callback()
def main():
    """
    Kurisu is 3515.games' development command-line interface.
    """


if __name__ == '__main__':
    # Only use when developing Kurisu itself. Otherwise, use the `kurisu` command.
    app()
