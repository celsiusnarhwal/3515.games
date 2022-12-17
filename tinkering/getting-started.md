# Getting Started

Before you can start messing with 3515.games' source code, you'll need to register a an application with Discord and
set up a proper development environment. I assume you know your way around the Discord Developer Portal and have some
basic knowledge of bot development.

## It's so simple, you can do it in seven succinct steps!

1. [Register an application with Discord](https://discord.com/developers/applications) and give it a bot account.
   I personally use separate applications, and thus bots, for development and production.
2. [Install Python](https://www.python.org/downloads/). 3515.games requires Python 3.11 or later.
3. Install [Poetry.](https://python-poetry.org)

    ```bash
    curl -sSL https://install.python-poetry.org | python
    ```

4. Clone this repository.

    ```bash
    git clone https://github.com/celsiusnarhwal/3515.games && cd 3515.games
    ```

5. Install 3515.games' dependencies.

    ```bash
    poetry install
    ```

6. Read [Secrets](secrets.md).
7. Start it up.
    ```bash
    doppler run -- poetry run python main.py
    ```
You're all set!