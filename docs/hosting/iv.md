---
icon: fontawesome/solid/box
---

# Chapter IV: Contain Your Enthusiasm

To self-host 3515.games in a way that *doesn't* make you want to tear your hair out, you'll need to stuff it and all
its dependencies into a nice little package that you can run on any operating system with next-to-zero effort.

The kind of package in question? It's called a **container**.

## Prerequsites

Before proceeding, make sure you have the following:

- [:fontawesome-brands-docker: Docker](https://docs.docker.com/get-docker)

## :fontawesome-solid-hammer: Building the Image

!!! warning

    Make sure Docker is running before proceeding.

There *should* be a `Dockerfile` at the root of your project. If it's somehow missing, create one with the following
contents:

```dockerfile
FROM python:3.11.1 "(1)!"

ENV POETRY_VERSION=1.4.1 "(2)!"
ENV POETRY_HOME=/opt/poetry "(3)!"
ENV PATH="${PATH}:${POETRY_HOME}/bin" "(4)!"

COPY . /app "(5)!"

WORKDIR /app/bot

RUN apt-get update && apt-get install -y apt-transport-https ca-certificates curl gnupg && \
    curl -sLf --retry 3 --tlsv1.2 --proto "=https" 'https://packages.doppler.com/public/cli/gpg.DE2A7741A397C129.key' | apt-key add - && \
    echo "deb https://packages.doppler.com/public/cli/deb/debian any-version main" | tee /etc/apt/sources.list.d/doppler-cli.list && \
    apt-get update && \
    apt-get -y install doppler "(6)!"

RUN curl -sSL https://install.python-poetry.org | python - && poetry install --only main "(7)!"

ENTRYPOINT ["doppler", "run", "--", "poetry", "run", "python", "main.py"] "(8)!"
```

1. The version of Python to be used inside the container. This should match the version specified in `pyproject.toml`.
2. The version of Poetry to be used inside the container. This should match the version installed on your local machine.
    ```bash
    poetry --version
    ```
3. Poetry will install to this directory inside the container.
4. Adds Poetry's executable to the system path.
5. Copies all files and directories in the project not excluded by `.dockerignore` to the `/app` directory within the container.
6. Installs the Doppler CLI inside the container. 
7. Installs Poetry and the dependencies 3515.games needs to run.
8. Starts 3515.games.

There *should* also be a `.dockerignore` file at the root of your project. If *that's* somehow missing, create one
with the following contents:

```docker
* "(1)!"

!bot/
!gps.py
!COPYING
!poetry.lock
!pyproject.toml "(2)!"
```

1. Ignores all files and directories in the project.
2. Explicitly does not ignore:

    - `bot/`
    - `gps.py`
    - `COPYING`
    - `poetry.lock`
    - `pyproject.toml`

    Only these files and directories will be included in the container.

Open up a terminal and run:

```bash
docker build . -t 3515.games:latest
```

This will build a **Docker image** of 3515.games. Think of it as an executable that starts 3515.games whenever you run
it. You can take this image to any machine with Docker installed and it will always work in exactly the same way,
every single time.

Try it out:

```bash
poe docker
```

Pretty cool, right?

Now it's time for the final step: taking this image and deploying it to the cloud.