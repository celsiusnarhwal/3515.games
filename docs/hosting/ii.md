---
icon: fontawesome/solid/leaf
---

# Chapter II: Environmental Activism

In this stage, you'll grab a copy of 3515.games' source code and set yourself up a development environment.

## Prerequisites

Before proceeding, make sure you have the folowing:

<div class="annotate" markdown>

- [:fontawesome-brands-git-alt: Git](https://git-scm.com/downloads) (1)
- [:fontawesome-brands-github: A GitHub account](https://github.com) 

</div>

1. If you're on macOS or Linux, there's a good chance Git is already installed. Take a moment to check:

    ```bash
    git --version
    ```

## :fontawesome-brands-python: Installing Python

3515.games currently requires [Python](https://python.org) 3.11.1 or later. If you already have that, feel free to
skip this section. Otherwise, read on.

=== ":fontawesome-brands-apple: macOS / :fontawesome-brands-linux: Linux"
    !!! danger "Do not use your system Python"
        If a version of Python came installed with your operating system, it's almost certainly too low for 3515.games.
    
    <div class="annotate" markdown>

    Install [asdf](https://asdf-vm.com/guide/getting-started.html)(1), then:
    
    ```bash
    asdf plugin add python
    asdf install python 3.11.1
    asdf global python 3.11.1
    ```

    Verify the installation worked:
        
    ```bash
    python --version
    ```
    
    </div>
    
    1. !!! info "Why not Python's official installer?"

            Using asdf guarantees that the `python` command will point to the appropriate version of Python.

            If you have a good reason or simply a strong preference to install Python through other means, feel free.
            This guide won't be supporting you along the way, though.

=== ":fontawesome-brands-windows: Windows"
    !!! danger "Do not use the Microsoft Store Python"
        The Microsoft Store distribution of Python is unsuitable for 3515.games.
    
    Install Python from [python.org/downloads](https://python.org/downloads), then verify the installation worked:
    
    ```powershell
    py --version
    ```

## :fontawesome-regular-code-fork: Forking the Repository

Forking 3515.games' repository (hereafter referred to as the "canonical repository") creates a full copy of it
in your own GitHub account that you can then do whatever you want with. (1)
{ .annotate }

1. Pursuant to the terms of the [AGPL](https://github.com/celsiusnarhwal/3515.games/blob/main/LICENSE.md), of course.

Head over to [celsiusnarhwal/3515.games](https://github.com/celsiusnarhwal/3515.games) and click the "Fork" button
in the top-right area of the page. Then follow the prompts and you're done. Pretty easy, right?

!!! info "The rest of this guide assumes your fork is named "3515.games""
    If you named your fork something else, it's up to you to figure out which instructions you need to change.

!!! warning "Your fork must remain public"
    Not that you can change the visibility of a forked GitHub repository to begin with, but 3515.games' license
    requires that if you self-host it, you have to make your copy of the source code, complete with any modifications, 
    available to anyone who wants it. For all practical purposes, this means your fork must remain public.

## :fontawesome-solid-download: Cloning the Repository

It's time to clone your forked repository — that is, create a copy of it on your local machine.


=== ":fontawesome-brands-git-alt: Git"
    ```bash
    git clone https://github.com/{YOUR_USERNAME}/3515.games # (1)!
    ```
    
    1. Replace `{YOUR_USERNAME}` with your GitHub username.

=== ":fontawesome-brands-github: GitHub CLI"
    ```bash
    gh repo clone 3515.games
    ```

=== ":simple-pycharm: PyCharm"
    From the main menu, go to **Get from VCS** > **GitHub** and select your fork. Then, select **Clone**.

=== ":simple-visualstudiocode: Visual Studio Code"
    Enter `gitcl` into the command pallette, then selct **Git: Clone** and then **Clone from GitHub**. When prompted
    for the repository URL, enter `{YOUR_USERNAME}/3515.games`. (1)
    { .annotate }
    
    1. Replace `{YOUR_USERNAME}` with your GitHub username.

## :fontawesome-duotone-spinner: Installing Dependencies

!!! warning
    All terminal commands throughout the rest of this guide must be run in the directory where you cloned 3515.games
    to.

Before you can run 3515.games, you'll need to install the third-party libraries it depends on.

First, install [Poetry](https://python-poetry.org).(1)
{ .annotate }

1. Other Python package managers, including pip, are strictly unsupported.

=== ":fontawesome-brands-apple: macOS / :fontawesome-brands-linux: Linux"
    ```bash
    curl -sSL https://install.python-poetry.org | python -
    ```

=== ":fontawesome-brands-windows: Windows"
    ```powershell
    (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py - # (1)!
    ```

    1. Make sure you're using PowerShell and not the legacy Command Prompt.

Verify the installation worked:

```bash
poetry --version
```

Then install 3515.games' dependencies:

```bash
poetry install --without docs # (1)!
```

1. `--without docs` tells Poetry to skip installing the dependencies required to build 3515.games' website (yes,
    the one you're looking at now). The website is made with the Insiders edition of 
    [Material for MkDocs](https://squidfunk.github.io/mkdocs-material), which is not free and requires additional
    configuration to install.

    TL;DR: Installing the website's dependencies will cause Poetry to fail, so leave them out.

## :fontawesome-solid-link: Linking Your Doppler Project

Remember the Doppler project you created back in [Part I](/hosting/doppler)? It's time to link it to your codebase.

```bash
doppler setup
```

Follow the prompts to link your Doppler project to your codebase. When asked to select a config, select `dev`.

## :fontawesome-solid-play: Running 3515.games

It's finally time for the moment you've been waiting for: actually running the damn thing.

=== ":simple-pycharm: PyCharm"
    In the Project tool window, right click on `bot/main.py` and select **Run 'main'**.

=== ":simple-visualstudiocode: Visual Studio Code"
    Open `bot/main.py` and press **F5**.

=== ":fontawesome-sharp-solid-terminal: Terminal"
    === ":fontawesome-brands-apple: macOS / :fontawesome-brands-linux: Linux"
        ```bash
        poetry run python bot/main.py
        ```

    === ":fontawesome-brands-windows: Windows"
        ```powershell
        poetry run py bot/main.py
        ```

If everything worked, you should see something like this in your console:

```
TypeError: join() argument must be str, bytes, or os.PathLike object, not 'NoneType'
```

Wait. That's not quite right.

Let's fix this, shall we?