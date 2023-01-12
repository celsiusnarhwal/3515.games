########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
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
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime
from difflib import SequenceMatcher
from enum import Enum

import discord
import git as pygit
import gitignorefile as gitignore
import inflect as ifl
import pyperclip
import semver
import tomlkit as toml
import typer
import wonderwords
from InquirerPy.base import Choice
from path import Path
from rich import print
from rich.progress import track

import kurisu.settings
import prompts
import shrine
import support
from kurisu.docs import get_docs_for_click
from settings import settings

inflect = ifl.engine()

here = Path(__file__).parent
root = here.parent

app = typer.Typer()
app.add_typer(kurisu.settings.app, name="settings")


@app.command(name="copyright")
def copyright(
    verbose: bool = typer.Option(
        None, "--verbose", "-v", help="Show the name of each changed file."
    ),
    quiet: bool = typer.Option(
        None,
        "--quiet",
        "-q",
        help="Suppress all output aside from errors. Overrides -v.",
    ),
    dry_run: bool = typer.Option(
        None,
        "--dry-run",
        "-n",
        help="Run as usual but without actually " "changing any files.",
    ),
):
    """
    Attach copyright notices to all non-gitignored Python source files.
    """

    def echo(*args, **kwargs):
        if not quiet:
            print(*args, **kwargs)

    def write(fp: Path, content: str):
        nonlocal changed
        changed += 1

        if verbose:
            echo(f"[bold yellow]Changed[/]: {file}")

        if not dry_run:
            fp.write_text(content)

    verbose = verbose and not quiet

    is_ignored = gitignore.parse(root / ".gitignore")
    changed = 0

    with shrine.Torii.kurisu() as torii:
        template = torii.get_template("copyright.jinja")
        notice = template.render(year=datetime.now().year).strip("\n") + "\n\n"

        for file in [f for f in root.walkfiles("*.py") if not is_ignored(f)]:
            ratio = SequenceMatcher(None, "".join(file.lines()[:6]), notice).ratio()

            if 0.9 <= ratio < 1:
                write(file, notice + "".join(file.lines()[6:]))
            elif ratio == 1:
                pass
            else:
                write(file, notice + file.text())

    if changed:
        output = (
            f"[green]Changed [bold]{changed}[/bold] {inflect.plural('file', changed)}"
        )
    else:
        output = "[green] No files changed"

    if dry_run:
        output += " (dry run)"

    echo(output)


class DocSite(str, Enum):
    DISCORD = "discord"
    PYCORD = "pycord"
    NUMPYDOC = "numpydoc"


@app.command(name="docs")
def docs(
    site: DocSite = typer.Argument(
        ..., help="The documentation site to open.", show_default=False
    )
):
    """
    Open the documentation for the Discord API, Pycord, or Numpydoc.
    """

    sites = {
        DocSite.DISCORD: "https://discord.com/developers/docs",
        DocSite.PYCORD: f"https://docs.pycord.dev/en/v{discord.__version__}",
        DocSite.NUMPYDOC: "https://numpydoc.readthedocs.io/en/latest/format.html",
    }

    typer.launch(sites[site])


@app.command(name="document", rich_help_panel="Meta Commands")
def document(
    ctx: typer.Context,
    output: pathlib.Path = typer.Option(
        here / "README.md",
        "--output",
        show_default=False,
        file_okay=True,
        dir_okay=False,
        help="The file to write the documentation to. " "Defaults to kurisu/README.md.",
    ),
    override: bool = typer.Option(
        None,
        "--override",
        "-o",
        help="Override the the file specified by --output if it already exists. "
        "If the file exists and you don't pass this option, "
        "you'll be asked if you want to override it.",
    ),
    copy: bool = typer.Option(
        None, "--copy", "-c", help="Copy the documentation to the clipboard."
    ),
) -> None:
    """
    Generate Kurisu's documentation.
    """
    click_obj = typer.main.get_command(app)
    click_docs = get_docs_for_click(obj=click_obj, ctx=ctx, name="kurisu")
    clean_docs = "".join(
        ["# Kurisu\n", *f"{click_docs.strip()}\n".splitlines(keepends=True)[1:]]
    )

    if copy:
        pyperclip.copy(clean_docs)
        print("[bold green]Docuemtation copied to clipboard[/]")

    if output.exists() and not (
        override or typer.confirm(f"{output} already exists. Override it?")
    ):
        raise typer.Exit()

    output.write_text(clean_docs)
    print(f"[bold green]Documentation saved to {output}[/]")


@app.command(name="invite")
def invite(
    production: bool = typer.Option(
        None,
        "--production",
        "-p",
        help="Generate an invite link for the " "production instance of 3515.games.",
    ),
    copy: bool = typer.Option(
        None, "--copy", "-c", help="Copy the invite link to the clipboard."
    ),
    launch: bool = typer.Option(
        None, "--open", "-o", help="Open the invite link in a web browser."
    ),
):
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


@app.command(name="licenses")
def licenses(
    output: pathlib.Path = typer.Option(
        None,
        "--output",
        "-o",
        help="The file to write the documentation to. If neither this "
        "nor -c are provided, the documentation will be "
        "printed to standard output.",
    ),
    copy: bool = typer.Option(
        None,
        "--copy",
        "-c",
        help="Copy the documentaton to the clipboard. If neither "
        "this nor -o are provided, the documentation will be "
        "printed to standard output.",
    ),
):
    """
    Create Markdown-formatted documentation of 3515.games' software licenses.
    """
    documents = json.loads(
        subprocess.run(
            "pip-licenses -f json --from=mixed --no-license-path --with-license-file",
            capture_output=True,
            shell=True,
        ).stdout
    )

    documents = sorted(documents, key=lambda d: d["Name"].casefold())

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
        "# Acknowledgements\n\n"
        "Questions or concerns regarding errors or inconsistencies in this automatically-generated "
        "document should be sent to hello@celsiusnarhwal.dev.<hr></hr>\n\n"
    )

    dependencies = [
        dep["name"]
        for dep in toml.load((root / "poetry.lock").open())["package"]
        if dep["category"] == "main"
    ]

    for doc in documents:
        if doc["Name"].casefold() in dependencies:
            license_file += f"## {doc['Name']}\n\n"

            if doc["LicenseText"] != "UNKNOWN":
                license_file += f"{doc['LicenseText']}\n\n".replace("#", "").replace(
                    "=", ""
                )
            else:
                for fallback in fallbacks:
                    if fallback in doc["License"]:
                        license_file += (
                            f"{doc['Name']} is licensed under the "
                            f"[{doc['License']}]({fallbacks[fallback]}).\n\n"
                        )

    license_file = re.sub(r"-{3,}", "\n\g<0>", license_file)

    if not (output or copy):
        print(license_file)
    else:
        if output:
            output.write_text(license_file)
            print(f"[bold green]License documentation saved to {output}[/]")

        if copy:
            pyperclip.copy(license_file)
            print("[bold green]License documentation copied to clipboard[/]")


@app.command(name="portal")
def portal():
    """
    Open 3515.games.dev on the Discord Developer Portal.
    """
    typer.launch(
        f"https://discord.com/developers/applications/{settings.app_id}/information/"
    )


@app.command(name="release", rich_help_panel="Dangerous Commands")
def release(
    dry_run: bool = typer.Option(
        None,
        "--dry-run",
        "-n",
        help="Run through the release flow without "
        "actually pushing a release or making any "
        "repository changes.",
    ),
):
    """
    Create a new release. This command is interactive only.
    """
    git = pygit.Repo().git
    github = support.bot_repo()

    last_version = semver.parse_version_info(github.get_latest_release().tag_name)
    new_version = semver.parse_version_info(support.pyproject()["version"])

    if new_version <= last_version:
        print(
            f"[bold red]Error:[/] [bold]Proposed version {new_version} is not greater than "
            f"latest version {last_version}[/bold]. Update pyproject.toml and try again."
        )
        raise typer.Exit(1)

    if dry_run:
        print(
            f"[bold blue]Notice:[/] This is a dry run. No release will be published and no changes will be made "
            f"to the repository.\n"
        )
    else:
        print(
            f"[bold yellow]Warning:[/] This is NOT a dry run. Proceed with caution.\n"
        )

    release_title = prompts.text(
        message="Enter a title for this release.",
        default=str(new_version),
        validate=lambda result: bool(result.strip()),
        invalid_message="You must enter a title.",
    ).execute()

    release_notes = None

    match prompts.select(
        message="How would you like to enter the release notes?",
        choices=[
            Choice(name="Write from scratch", value="scratch"),
            Choice(name="Import from a file", value="file"),
        ],
    ).execute():
        case "scratch":
            prompts.text(
                "Kurisu will open your default text editor. Save the file and close the editor "
                "when you're done. Press Enter to continue."
            ).execute()
            release_notes = typer.edit(require_save=False, extension=".md")

            if not release_notes.strip():
                print("[bold red]Error:[/] [bold]Release notes cannot be empty.[/bold]")
                raise typer.Exit(1)
        case "file":
            release_notes = prompts.filepath(
                message="Enter the path to a Markdown or plain text file.",
                validate=lambda result: Path(result).ext in [".md", ".txt"]
                and Path(result).text().strip(),
                invalid_message="The file must be an existing, non-empty, Markdown or plain text file.",
                filter=lambda result: Path(result).text(),
            ).execute()

    if not prompts.confirm(
        "Confirm you understand that you are merging the development branch into the main branch "
        "and that the development branch's codebase, as it was last committed, will be deployed to the "
        "production instance of 3515.games."
    ).execute():
        raise typer.Exit()

    passphrase = " ".join(wonderwords.RandomWord().random_words(4))

    prompts.text(
        message=f"Enter the passphrase located at the bottom of your terminal.",
        long_instruction=f"Passphrase: {passphrase}",
        validate=lambda result: result == passphrase,
        invalid_message="Incorrect passphrase.",
    ).execute()

    if not prompts.select(
        message="Final confirmation. There's no going back after this.",
        choices=[
            Choice(name="Push it", value=True),
            Choice(name="Never mind", value=False),
        ],
    ).execute():
        raise typer.Exit()

    if not dry_run:
        for _ in track(
            description="Pushing...",
            sequence=[
                git.checkout(github.default_branch),
                git.merge("dev"),
                git.push(),
                github.create_git_tag_and_release(
                    tag=str(new_version),
                    release_name=release_title,
                    release_message=release_notes,
                    object=github.get_branch(github.default_branch).commit.sha,
                    type="commit",
                ),
            ],
        ):
            pass

    print(f"[bold green]Released 3515.games {new_version}[/]")


@app.callback()
def main():
    """
    Kurisu is 3515.games' development command-line interface.
    """


if __name__ == "__main__":
    # Only use when developing Kurisu itself. Otherwise, use the `kurisu` command.
    app()
