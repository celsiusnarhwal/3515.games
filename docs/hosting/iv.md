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
--8<--
Dockerfile
--8<--
```

There *should* also be a `.dockerignore` file at the root of your project. If *that's* somehow missing, create one
with the following contents:

```docker
--8<--
.dockerignore
--8<--
```

```bash
docker build . -t 3515.games:latest
```

This will build a **Docker image** of 3515.games. Think of it as an executable that starts 3515.games whenever you run
it. You can take this image to any machine with Docker installed and it will always work in exactly the same way,
every single time.

Try it out:

=== ":fontawesome-brands-apple: macOS / :fontawesome-brands-linux: Linux"
    
    ```bash
    docker run --rm -it -e DOPPLER_TOKEN="$(doppler configs tokens create docker --max-age 1m --plain)" 3515.games:latest
    ```

=== ":fontawesome-brands-windows: Windows"
    
    ```powershell
    docker run --rm -it -e DOPPLER_TOKEN=(doppler configs tokens create docker --max-age 1m --plain) 3515.games:latest
    ```

Pretty cool, right?

Now it's time for the final step: taking this image and deploying it to the cloud.