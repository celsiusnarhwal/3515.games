# Chapter III: Late Registration

If you know anything about Discord bot development, you probably expected this guide to start here. Surprise?

Before 3515.games can do anything useful, you'll need to create an application for it on the Discord Developer Portal.

## Prerequisites

Before proceeding, make sure you have the following:

- [:fontawesome-brands-discord: A Discord account](https://discord.com)

## :fontawesome-solid-sparkles: Creating Your Application

Head to the [Discord Developer Portal](https://discord.com/developers) and click the **New Application** button in
the top-right. Give your application a name (it doesn't matter what it is), agree to the terms, and click **Create**.

<figure markdown>
  ![Image title](/assets/img/hosting/app.png)
  <figcaption>A fancy new application.</figcaption>
</figure>

Note the **application ID**. Copy it, then open a terminal and run:

```bash
doppler secrets set BOT_APP_ID {APP_ID} # (1)!
```

1. Replace `{APP_ID}` with your application's ID.

### :fontawesome-solid-key: Getting a Token

Head over to the **Bot** tab of your application's page and click **Add Bot**. Confirm the action and your application
will have a cool new bot attached to it. You can change the bot's username and avatar here, but that's not important
right now.

What *is* important is that "View Token" button, just below your bot's username. The long string of characters
revealed when you click it is your bot's **token**.

!!! danger "Keep this a secret to everybody"
    **Never share your bot's token with anyone.** Anyone who has your bot's token has full control over your bot.
    
    If you token is lost or compromised, you'll have to generate a new one, and your bot will stop working until
    you update the token in its code.

Copy your token to your clipboard, then head back to your terminal and run:

```powershell
doppler secrets set BOT_TOKEN {TOKEN} # (1)!
```

1. Replace `{TOKEN}` with your bot's token.

### :fontawesome-solid-envelope-open-text: Inviting Your Bot

Paste the following URL into your browser: (1)
{ .annotate }

1. Replace `{APP_ID}` with your application's ID. Do not change anything else.

```text
https://discord.com/api/oauth2/authorize?client_id={APP_ID}&permissions=326484094224&scope=bot%20applications.commands
```

Follow the prompts to invite your bot to any server where you have the appropriate permissions.

## :fontawesome-solid-play: Running 3515.games

Let's try that again, shall we?

=== ":simple-pycharm: PyCharm"
    1. Edit the `main` run configuration as follows:
        - Add an environment variable named `DOPPLER_ENV` with a value of `1`
        - Check **Emulate terminal in output console**

    2. In the Project tool window, right click on `bot/main.py` and select **Run 'main'**.

=== ":simple-visualstudiocode: Visual Studio Code"
    1. At the root of your project, create a `launch.json` file with the following contents:
            
        ```json
        {
            "version": "0.2.0",
            "configurations": [
                {
                    "name": "Python: 3515.games",
                    "type": "python",
                    "request": "launch",
                    "program": "${workspaceFolder}/bot/main.py",
                    "env": {
                        "DOPPLER_ENV": "1"
                    }
                }
            ]
        }
        ```

    1. Open `bot/main.py` and press **F5**.

=== ":fontawesome-sharp-solid-terminal: Terminal"
    === ":fontawesome-brands-apple: macOS / :fontawesome-brands-linux: Linux"
        ```bash
        doppler run -- poetry run python bot/main.py
        ```
    
    === ":fontawesome-brands-windows: Windows"
        ```powershell
        doppler run -- poetry run py bot/main.py
        ```

If everything worked, you should see something like this in your console:

```text
3515.games.dev is ready to play! 🎉
```

It works. Awesome. Now you can head over to the Discord server you invited it to and start playing around with it.

But of course, you came here to learn how to self-host it. We're not there quite yet.

Bear with me for just a little longer.