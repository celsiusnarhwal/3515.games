########################################################################################################################
#                         Copyright (C) 2023-present celsius narhwal <hello@celsiusnarhwal.dev>                        #
#  This notice may not be altered or removed except by or with the express written permission of the copyright holder. #
#                                      For more information, see the COPYING file.                                     #
########################################################################################################################

import json
import subprocess

import prompts
import typer
from path import Path
from rich import print

import shrine

here = Path(__file__).parent
root = here.parent

app = typer.Typer()


@app.command(name="new")
def new(
    config: str = typer.Option(
        None,
        "--config",
        "-c",
        show_default=False,
        help="The name of the Doppler configuration to create a "
        "settings configuration for. You'll be prompted "
        "for this if you don't provide it.",
    ),
    description: str = typer.Option(
        None,
        "--description",
        "-d",
        show_default=False,
        help="The description for the new settings configuration. "
        "You'll be prompted for this if you don't provide it.",
    ),
):
    """
    Create a new settings configuration.
    """
    configs_dir = root / "settings" / "envs"

    envs_json = json.loads(
        subprocess.run(
            "doppler environments --json --no-read-env", shell=True, capture_output=True
        ).stdout.decode()
    )

    configs_json = json.loads(
        subprocess.run(
            "doppler configs --json --no-read-env", shell=True, capture_output=True
        ).stdout.decode()
    )

    if config:
        match next((c for c in configs_json if c["name"] == config), None):
            case None:
                print(f"[bold red]Error:[/] Unknown Doppler configuration: {config}")
                raise typer.Exit(1)
            case _ as config_info:
                environment = config_info["environment"]
                if (configs_dir / environment / config).with_suffix(".py").exists():
                    print(
                        f"[bold red]Error:[/] A settings configuration for {environment}/{config} already exists."
                    )
                    raise typer.Exit(1)
    else:
        environment = prompts.rawlist(
            message="Select a Doppler environment.",
            choices=[env["id"] for env in envs_json],
        ).execute()

        config = prompts.rawlist(
            message="Select a Doppler configuration.",
            choices=[
                c["name"] for c in configs_json if c["environment"] == environment
            ],
            validate=lambda result: not (configs_dir / environment / result)
            .with_suffix(".py")
            .exists(),
            invalid_message="This Doppler configuration already has a settings configuration.",
        ).execute()

    description = (
        description
        or prompts.text(
            message="Enter a description for this settings configuration.",
            validate=lambda result: bool(result),
            invalid_message="You must enter a description.",
        ).execute()
    )

    with shrine.Torii.kurisu() as torii:
        template = torii.get_template("settings.py.jinja")
        env_dir = (configs_dir / environment).makedirs_p()
        env_dir.joinpath("__init__.py").touch()
        env_dir.joinpath(config).with_suffix(".py").write_text(
            template.render(description=description)
        )

    print(f"[green]Created settings configuration for {environment}/{config}[/green].")


@app.command(name="sync")
def sync():
    """
    Remove settings configurations that lack a corresponding Doppler configuration.
    """
    changed = False

    configs_dir = root / "settings" / "envs"

    envs_json = json.loads(
        subprocess.run(
            ["doppler", "environments", "--json"], capture_output=True
        ).stdout.decode()
    )
    configs_json = json.loads(
        subprocess.run(
            ["doppler", "configs", "--json"], capture_output=True
        ).stdout.decode()
    )

    envs = [env["id"] for env in envs_json]
    configs = [config["name"] for config in configs_json]

    for directory in configs_dir.dirs():
        if directory.name not in envs:
            directory.rmtree()
            changed = True
        else:
            for file in directory.files():
                if file.stem not in configs and file.name != "__init__.py":
                    file.remove()
                    changed = True

            if (
                len(directory.files()) == 1
                and directory.files()[0].name == "__init__.py"
            ):
                directory.rmtree()
                changed = True

    if changed:
        print("[green]Settings configurations synced.[/green]")
    else:
        print(
            "[yellow]Settings configurations already in sync. No changes made.[/yellow]"
        )


@app.callback()
def main():
    """
    Manage settings configurations.
    """
    try:
        subprocess.check_output(["doppler"], shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        print(
            "[red]Error:[/] The Doppler CLI doesn't appear to be installed. Install it, set it up, and try again. "
            "https://docs.doppler.com/docs/cli"
        )
