########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

"""
Kurisu, 3515.games' development CLI, provides command-line shortcuts for common development tasks.
"""

import json
import os
import pathlib
import platform
import re
import subprocess
import textwrap
import urllib.parse
from difflib import SequenceMatcher
from enum import StrEnum, auto
from importlib import metadata

import discord.utils
import git
import inflect as ifl
import marko
import pendulum
import pyperclip
import requests
import semver
import tomlkit as toml
import typer
from bs4 import BeautifulSoup
from dict_deep import deep_get
from halo import Halo
from path import Path
from pydantic.dataclasses import dataclass
from rich import print
from yarl import URL

import shrine
import support
from gps import Routes
from keyboard import *
from kurisu.docs import get_docs_for_click
from settings import settings

inflect = ifl.engine()

app = typer.Typer(no_args_is_help=True, rich_markup_mode="rich")


class LogSymbols(StrEnum):
    INFO = ("[blue]ℹ[/]",)
    SUCCESS = ("[green]✔[/]",)
    WARNING = ("[yellow]⚠[/]",)
    ERROR = "[red]✖[/]"


class DocSite(StrEnum):
    ATTRS = auto()
    DISCORD = auto()
    FONTAWESOME = auto()
    MATERIAL = auto()
    MATERIAL_ICONS = "icons"
    NUMPYDOC = auto()
    PYCORD = auto()
    PYDANTIC = auto()

    @property
    def url(self) -> str:
        return {
            DocSite.ATTRS: f"https://attrs.org/en/{metadata.version('attrs')}",
            DocSite.DISCORD: "https://discord.com/developers/docs",
            DocSite.PYCORD: f"https://docs.pycord.dev/en/v{metadata.version('py-cord')}",
            DocSite.PYDANTIC: "https://docs.pydantic.dev",
            DocSite.MATERIAL: "https://squidfunk.github.io/mkdocs-material/getting-started",
            DocSite.MATERIAL_ICONS: "https://squidfunk.github.io/mkdocs-material/reference/icons-emojis/",
            DocSite.NUMPYDOC: "https://numpydoc.readthedocs.io/en/latest/format.html",
            DocSite.FONTAWESOME: "https://fontawesome.com/search",
        }[self]


@app.command(name="check")
def check():
    """
    Check certain release criteria.
    """

    @dataclass
    class CheckResult:
        result: bool
        info: str = None

        def __bool__(self):
            return self.result

    checks = []

    def checkmark(func: Callable):
        checks.append(func)
        return func

    @checkmark
    def check_version():
        old = semver.parse_version_info(support.repo().get_latest_release().tag_name)
        new = semver.parse_version_info(support.version())

        return CheckResult(
            new > old,
            f"The project version is too low. Use [cyan]poetry version[/] to bump it to "
            f"[cyan]{old.bump_patch()}[/] or higher.",
        )

    @checkmark
    def check_changelog():
        with Routes.root():
            with Path("CHANGELOG.md").open() as file:
                changelog = BeautifulSoup(
                    marko.render(marko.parse(file.read())), "html.parser"
                )

        version = support.version()

        result = bool(
            discord.utils.find(
                lambda heading: version in heading.text, changelog.find_all("h2")
            )
        )

        return CheckResult(
            result or not check_version().result,
            f"CHANGELOG.md is missing an entry for [cyan]{version}[/].",
        )

    @checkmark
    def check_copyright():
        result = (
            subprocess.run(
                "kurisu copyright -nvz".split(), capture_output=True
            ).returncode
            == 0
        )

        return CheckResult(
            result,
            "Copyright notices are out-of-date. Run [cyan]kurisu copyright[/].",
        )

    @checkmark
    def check_docker_python():
        with Routes.root():
            result = (
                Path("Dockerfile").lines()[0].split()[1].split(":")[1]
                == platform.python_version()
            )

            return CheckResult(
                result,
                f"The Python version in the Dockerfile is incorrect. Change it to "
                f"[cyan]{platform.python_version()}[/].",
            )

    @checkmark
    def check_docker_poetry():
        with Routes.root():
            poetry_line = discord.utils.find(
                lambda line: "ENV POETRY_VERSION" in line, Path("Dockerfile").lines()
            )

            docker_poetry = poetry_line.split("=")[1].strip()

        version_pattern = re.compile(r"Poetry \(version (\d+\.\d+\.\d+)\)")

        installed_poetry = version_pattern.match(
            subprocess.run(
                "poetry --version".split(), capture_output=True
            ).stdout.decode()
        ).group(1)

        return CheckResult(
            docker_poetry == installed_poetry,
            f"The Poetry version in the Dockerfile is incorrect. Change it to [cyan]{installed_poetry}[/].",
        )

    @checkmark
    def check_actions_poetry():
        with Routes.root():
            action = ".github/workflows/docs.yml"

            poetry_line = discord.utils.find(
                lambda line: "pipx install poetry" in line,
                Path(action).lines(),
            )

            actions_poetry_pattern = re.compile(r"pipx install poetry==(\d+\.\d+\.\d+)")
            actions_poetry = actions_poetry_pattern.search(poetry_line).group(1)

        version_pattern = re.compile(r"Poetry \(version (\d+\.\d+\.\d+)\)")

        installed_poetry = version_pattern.match(
            subprocess.run(
                "poetry --version".split(), capture_output=True
            ).stdout.decode()
        ).group(1)

        return CheckResult(
            actions_poetry == installed_poetry,
            f"The Poetry version in {action} is incorrect. Change it to [cyan]{installed_poetry}[/].",
        )

    with Routes.root():
        if git.Repo().active_branch.name != "dev":
            print(
                "[bold red]You must be on the [cyan]dev[/] branch to use this commmand.[/]"
            )
            raise typer.Exit(1)

    with Halo(text="Running checks...", spinner="dots") as spinner:
        if not all(checks := [check() for check in checks]):
            spinner.stop()

            for res in checks:
                if not res:
                    print(f"{LogSymbols.ERROR} {res.info}")

            raise typer.Exit(1)

        spinner.succeed("All checks passed!")


@app.command(name="copyright")
def copyright(
    nonzero: bool = typer.Option(
        None, "--nonzero", "-z", help="Exit nonzero if files are changed."
    ),
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
        local_changed = False

        if not dry_run:
            pre = fp.text()

            fp.write_text(content)
            subprocess.run(
                f"black {fp}".split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT,
            )

            if fp.text() != pre:
                changed += 1
                local_changed = True
        else:
            if (
                fp.text()
                != subprocess.check_output(f"black --code {content}".split()).decode()
            ):
                changed += 1
                local_changed = True

        if local_changed and verbose:
            echo(f"[bold yellow]Changed[/]: {file}")

    verbose = verbose and not quiet
    changed = 0

    with shrine.Torii.kurisu() as torii:
        template = torii.get_template("copyright.jinja")
        notice = template.render() + "\n\n"

        with Routes.root() as root, git.Repo() as repo:
            for file in [f for f in root.walkfiles("*.py") if not repo.ignored(f)]:
                ratio = SequenceMatcher(None, "".join(file.lines()[:6]), notice).ratio()

                if 0.9 <= ratio < 1:
                    write(file, notice + "".join(file.lines()[6:]))
                elif ratio != 1:
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

    if nonzero and changed:
        raise typer.Exit(1)


@app.command(name="docs", no_args_is_help=True)
def docs(
    site: DocSite = typer.Argument(
        ..., help="The documentation site to open.", show_default=False
    )
):
    """
    Open frequently-used documentation sites.
    """

    typer.launch(site.url)


@app.command(name="document")
def document(
    ctx: typer.Context,
    output: pathlib.Path = typer.Option(
        Routes.kurisu() / "README.md",
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
        doppler_token = (
            subprocess.check_output(
                "doppler configs tokens create kurisu --config prd --max-age 1m --plain".split()
            )
            .decode()
            .strip()
        )

        secret = requests.get(
            "https://api.doppler.com/v3/configs/config/secret",
            headers={"Authorization": f"Bearer {doppler_token}"},
            params={
                "project": os.getenv("DOPPLER_PROJECT"),
                "config": "prd",
                "name": "BOT_APP_ID",
            },
        )

        app_id = deep_get(secret.json(), "value.raw")
    else:
        app_id = settings.app_id

    base_url = "https://discord.com/api/oauth2/authorize"

    params = {
        "client_id": app_id,
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
def licenses():
    """
    Generate the Markdown source for https://3515.games/legal/acknowledgements/.
    """
    documents = json.loads(
        subprocess.run(
            "pip-licenses -f json --from=mixed --no-license-path --with-license-file".split(),
            capture_output=True,
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

    front_matter = """
    ---
    icon: fontawesome/solid/stars
    hide:
        - footer
    search:
        exclude: true
    ---
    """

    license_file = "\n\n# Acknowledgements\n\n## Third-Party Software\n\n"

    with Routes.root() as root:
        dependencies = [
            dep["name"]
            for dep in toml.load((root / "poetry.lock").open())["package"]
            if dep["category"] == "main"
        ]

        for doc in documents:
            if doc["Name"].casefold() in dependencies:
                license_file += f"### {doc['Name']}\n\n"

                if doc["LicenseText"] != "UNKNOWN":
                    license_file += f"{doc['LicenseText']}\n\n".replace(
                        "#", ""
                    ).replace("=", "")
                else:
                    for fallback in fallbacks:
                        if fallback in doc["License"]:
                            license_file += (
                                f"{doc['Name']} is licensed under the "
                                f"[{doc['License']}]({fallbacks[fallback]}).\n\n"
                            )

        with support.Assets.kurisu():
            license_file += "<hr></hr>\n\n" + Path("acknowledgements.md").read_text()

        license_file = textwrap.dedent(front_matter).strip() + re.sub(
            r"-{3,}", "\n\g<0>", license_file
        )

        (root / "docs" / "legal" / "acknowledgements.md").write_text(license_file)


@app.command(name="notes")
def notes():
    """
    Generate release notes.
    """
    version = support.version()
    changelog = URL("https://3515.games/changelog").with_fragment(
        version.replace(".", "-")
    )

    notes = f"""
    This is 3515.games {version}.
    
    For release notes, see the [changelog]({changelog}).
    """

    pyperclip.copy(textwrap.dedent(notes).strip())

    print(f"[bold green]Release notes copied to clipboard[/]")


@app.command(name="portal")
def portal():
    """
    Open 3515.games.dev on the Discord Developer Portal.
    """
    typer.launch(
        f"https://discord.com/developers/applications/{settings.app_id}/information/"
    )


@app.command(name="vercel")
def vercel():
    """
    Open the latest preview deploymet of 3515.games' website.
    """
    typer.launch("https://3515-games-celsiusnarhwal.vercel.app/")


@app.callback(
    epilog=f"Kurisu © {pendulum.now().year} celsius narhwal. Thank you kindly for your attention."
)
def main():
    """
    Kurisu is 3515.games' development command-line interface.
    """


if __name__ == "__main__":
    # Only use when developing Kurisu itself. Otherwise, use the `kurisu` command.
    app()
