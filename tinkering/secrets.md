# Secrets

Secrets are sensitive pieces of information that would pose security risks if they were stored in plain text
(for example, 3515.games' bot token). Secrets are referenced in the source code like:

```py
os.getenv("SECRET_NAME")
```

3515.games uses [Doppler](https://doppler.com) for secrets management. This is enforced by
[`settings/__init.py__`](../settings/__init__.py), which will block 3515.games from starting up if it's not running
in a valid Doppler environment.

While you are free to change all this and manage secrets however you want, this document will explain what
I believe to be the best way of doing it.

## Prerequisites

- A [Doppler](https://dashboard.doppler.com/register) account. The free tier is *way* more than sufficient.
- A [new, empty, Doppler project](https://docs.doppler.com/docs/create-project) just for 3515.games.
- Two configurations in your Doppler project — one named `dev` and one
  named `prd` for development and production, respectively. By default, 3515.games requires the active Doppler
  configuration to be named either `dev` or `prd` and will refuse to start if this isn't the case.

## Referenced Secrets

3515.games references the following secrets:[^1]

<details>
    <summary><code>BOT_TOKEN</code></summary>
    <p>
        3515.games' bot token as provided by the Discord Developer Portal. Used to authenticate 3515.games to the 
        Discord API, which is a prerequsite to doing literally anything useful. I probably don't need to tell you
        that this should absolutely never ever be shared with anyone or checked into any kind of version control.
    </p>
</details>

<details>
    <summary><code>GITHUB_TOKEN</code></summary>
    <p>
        A <a href="https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token">GitHub personal access token</a>.
        This token allows 3515.games to make authenticated requests to the GitHub API through your GitHub account.
        This is used for fetching information like release notes and repository URLs. Unlike <code>BOT_TOKEN</code>,
        failing to provide this will not burn the whole house down, but <i>may</i> render some functionality unusable.
    </p>
</details>

Create those secrets in the `dev` and `prd` configurations of your Doppler project and fill them in with appropriate
values. If you use separate bots for development and production, make sure to use the correct tokens for each
environment.

## In Development

To use your secrets in development, you'll need the [Doppler CLI](https://docs.doppler.com/docs/cli).

Once you've installed the Doppler CLI, log into your Doppler account:

```bash
doppler login
```

Then, run the following command in 3515'games' root directory:

```bash
doppler setup
```

Follow the prompts to select your Doppler project and the `dev` configuration.

From here on out, whenever you start 3515.games, you'll need to use `doppler run`.

```bash
doppler run -- poetry run python main.py
```

That's it. Doppler will inject you secrets at runtime and you won't have to worry about anything else.

Unless you use PyCharm or Visual Studio Code, that is.

### PyCharm and Visual Studio Code

PyCharm and Visual Studio Code require some extra configuration to work with Doppler.

To use Doppler with either of these editors, you'll need [doppler-env](https://pypi.org/project/doppler-env). Because
I use PyCharm, doppler-env is already listed as a development dependency in [`pyproject.toml`](../pyproject.toml) and
should have been installed when you [set up your development environment](getting-started.md). If you don't have it,
you know what to do:

```bash
poetry add doppler-env --group dev
```

Once doppler-env is installed, edit your run configuration for [`main.py`](../main.py) to add an environment variable
named `DOPPLER_ENV` with a value of `1`. (Instructions: [PyCharm](https://www.jetbrains.com/help/pycharm/run-debug-configuration.html) | [Visual Studio Code](https://code.visualstudio.com/docs/editor/debugging#_launch-configurations))

That's it. Just run `main.py` like usual and Doppler will inject your secrets at runtime. If you ever want

(P.S. You don't need to worry about the `doppler run` command. Your run configuration will suffice.)

## In Production

### Using Integrations

If Doppler has an integration for your hosting provider (and it probably does), you can just connect your Doppler
account to your hosting provider and you're done.
See [Doppler's documentation on integrations](https://docs.doppler.com/docs/integrations). Make sure you use your
production configuration.

The official instance of 3515.games is hosted on [Railway](https://railway.app), for which Doppler has an integration.

### Using Docker

If your hosting provider supports Docker builds, you can edit 3515.games' [Dockerfile](../Dockerfile) to install
the Doppler CLI at build time.

Add this command somewhere between the `FROM` and `ENTRYPOINT` instructions:

```dockerfile
RUN (curl -Ls --tlsv1.2 --proto "=https" --retry 3 https://cli.doppler.com/install.sh || wget -t 3 -qO- https://cli.doppler.com/install.sh) | sh
```

Then edit the `ENTRYPOINT` instruction to use `doppler run`:

```dockerfile
ENTRYPOINT ["doppler", "run", "--", "poetry", "run", "python", "main.py"]
```

In the Doppler dashboard, [create a service token](https://docs.doppler.com/docs/service-tokens) for your production
configuration. Use your hosting provider's faculties to create an environment variable named `DOPPLER_TOKEN` and fill
it with your service token.

At runtime, the Doppler CLI will honor the `DOPPLER_TOKEN` environment variable and inject your secrets like usual.

### If All Else Fails

If Doppler doesn't integrate with your hosting provider and Docker builds aren't an option, you may be in a bit of a
tight spot. [Contact Doppler support](mailto:support@doppler.com) and ask nicely if they would consider adding an
integration for your hosting provider. If you're hosting 3515.games on your own server (meaning one that actually
belongs to you, personally), you've hopefully realized that you can just use the Doppler CLI like in
development — or even better, install Docker and follow [those instructions](#using-docker). Of course, you can always
manage your secrets manually (though I don't recommend it).

Or, ideally, switch to a hosting provider that doesn't suck. 🙃

[^1]: Truthfully, `GITHUB_TOKEN` may be a holdover from when 3515.games' repository was private during its initial development
and thus required authentication to access. You may be able to get away with not providing this. Who knows. I haven't
tested it. lmao
