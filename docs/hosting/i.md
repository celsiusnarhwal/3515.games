---
icon: fontawesome/solid/lock
---

# Chapter I: A Secret to Everybody

First, you'll need to create an account with the secrets management platform [Doppler](https://doppler.com).
Once you're signed up, create a project for 3515.games. By default, your project will have three environments:
`dev`, `stg`. and `prd` — short for development, staging, and production, respectively. We'll come back to all this
later.

For now, go ahead and install the Doppler CLI.

=== ":fontawesome-brands-apple: macOS"
    Install [Homebrew](https://brew.sh), then:
    
    ```bash
    brew install gnupg dopplerhq/cli/doppler
    ```

=== ":fontawesome-brands-windows: Windows"
    Install [Scoop](https://scoop.sh), then:
    
    ```bash
    scoop bucket add doppler https://github.com/DopplerHQ/scoop-doppler.git
    scoop install doppler
    ```

=== ":simple-debian: Debian / :fontawesome-brands-ubuntu: Ubuntu"
    ```bash
    sudo apt-get update && sudo apt-get install -y apt-transport-https ca-certificates curl gnupg
    curl -sLf --retry 3 --tlsv1.2 --proto "=https" 'https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key' | sudo apt-key add -
    echo "deb https://packages.doppler.com/public/cli/deb/debian any-version main" | sudo tee /etc/apt/sources.list.d/doppler-cli.list
    sudo apt-get update && sudo apt-get install doppler
    ```

=== ":fontawesome-brands-fedora: Fedora / :fontawesome-brands-redhat: Red Hat / :fontawesome-brands-centos: CentOS"
    ```bash
    sudo rpm --import 'https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key'
    curl -sLf --retry 3 --tlsv1.2 --proto "=https" 'https://packages.doppler.com/public/cli/config.rpm.txt' | sudo tee /etc/yum.repos.d/doppler-cli.repo
    sudo yum update && sudo yum install doppler
    ```

=== ":fontawesome-sharp-solid-terminal: Shell Script"
    You should generally prefer one of the other options before resorting to this one. This doesn't work on Windows. (1)
    { .annotate }
    
    1. It may work on WSL, but we're not covering that here.

    Install [curl](https://curl.se/) and [GnuPG](https://gnupg.org/), then:

    ```bash
    (curl -Ls --tlsv1.2 --proto "=https" --retry 3 https://cli.doppler.com/install.sh || wget -t 3 -qO- https://cli.doppler.com/install.sh) | sudo sh
    ```

Verify the CLI was installed by checking it's version:

```bash
doppler --version
```

Then connect the CLI to your Doppler account:

```bash
doppler login
```

Cool. On to the next step.