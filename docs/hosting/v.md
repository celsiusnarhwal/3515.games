---
icon: fontawesome/solid/train-tunnel
---

# Chapter V: All Aboard

## Prerequisites

Before proceeding, make sure you have the following:

- [:simple-railway: A Railway account](https://railway.app)

## :fontawesome-solid-floppy-disk: Saving Your Progress

At this point, it's time to to commit any changes you've made to Git and push them to GitHub.

=== ":fontawesome-brands-git-alt: Git"
    ```bash
    git add -A && git commit -m "{COMMIT_MESSAGE}" # (1)!
    git push -u origin main
    ```

    1. Replace `{COMMIT_MESSAGE}` with a commit message.

=== ":simple-pycharm: PyCharm"
    Open the **Commit** window (++control++ + ++k++ / ++command++ + ++k++), select the files you want to commit, and enter a commit message. Then, click **Commit and Push** > **Push**.

=== ":simple-visualstudiocode: Visual Studio Code"
    Open the **Source Control** tab (++control++ + ++shift++ + ++g++ / ++command++ + ++shift++ + ++g++),
    select the files you want to commit, and enter a commit message, then
    press ++control++ + ++enter++ / ++command++ + ++enter++ to make a commit.
    Then, open the **...** menu and click **Push**.


## :fontawesome-solid-rocket-launch: Deploying to Railway

### :fontawesome-solid-database: Provisioning a Database

Open the Railway dashboard and click **New Project**, then click **Provision PostgreSQL**.

### :fontawesome-solid-link: Linking Your Doppler Project <small>again</small>

[Create a new Railway API Token](https://railway.app/account/tokens) and copy it to your clipboard.

Then, open up the Doppler dashboard to the project you created for 3515.games, this time using the `prd` config. 
In the **Integrations** tab, click **+ Add Sync** and select **Railway**. Name your token whatever you want, then
paste it into the **API Token...** field and click **Connect**.

Configure the settings on the next screen as follows:

- **Railway Project**: The one you just created.
- **Railway Environment**: Leave as is.
- **Config to sync**: `prd`
- **Import Options**: Import, Preferring Doppler

Now head back to your Railway project and click **New**. Select **GitHub Repo**, then select your fork of 3515.games.

...and that's it! Railway will build and deploy 3515.games using the `Dockerfile` at your repository's root.
