# Kurisu

Kurisu is 3515.games' development command-line interface.

**Usage**:

```console
$ kurisu [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion [bash|zsh|fish|powershell|pwsh]`: Install completion for the specified shell.
* `--show-completion [bash|zsh|fish|powershell|pwsh]`: Show completion for the specified shell, to copy it or customize the installation.
* `--help`: Show the help message and exit.

**Commands**:

* [`copyright`](#kurisu-copyright): Attach copyright notices to all non-gitignored Python source files.
* [`docs`](#kurisu-docs): Generate Kurisu's documentation.
* [`invite`](#kurisu-invite): Generate an invite link for 3515.games. By default, this generates an invite link for the development instance.
* [`licenses`](#kurisu-licenses): Create Markdown-formatted documentation of 3515.games' software licenses.
* [`portal`](#kurisu-portal): Open the Discord Developer Portal.
* [`release`](#kurisu-release): Create a new release. This command is interactive only.
* [`settings`](#kurisu-settings): Manage settings configurations.

## `kurisu copyright`

Attach copyright notices to all non-gitignored Python source files.

**Usage**:

```console
$ kurisu copyright [OPTIONS]
```

**Options**:

* `-v, --verbose`: Show the name of each changed file.
* `-q, --quiet`: Suppress all output aside from errors. Overrides -v.
* `-n, --dry-run`: Run as usual but without actually changing any files.
* `--help`: Show the help message and exit.

## `kurisu docs`

Generate Kurisu's documentation.

**Usage**:

```console
$ kurisu docs [OPTIONS]
```

**Options**:

* `--output FILE`: The file to write the documentation to. Defaults to kurisu/README.md.
* `-o, --override`: Override the the file specified by -o if it already exists. If the file exists and you don't pass this option, you'll be asked if you want to override it.
* `-c, --copy`: Copy the documentation to the clipboard.
* `--help`: Show the help message and exit.

## `kurisu invite`

Generate an invite link for 3515.games. By default, this generates an invite link for the development instance.

**Usage**:

```console
$ kurisu invite [OPTIONS]
```

**Options**:

* `-p, --production`: Generate an invite link for the production instance of 3515.games.
* `-c, --copy`: Copy the invite link to the clipboard.
* `-o, --open`: Open the invite link in a web browser.
* `--help`: Show the help message and exit.

## `kurisu licenses`

Create Markdown-formatted documentation of 3515.games' software licenses.

**Usage**:

```console
$ kurisu licenses [OPTIONS]
```

**Options**:

* `-o, --output PATH`: The file to write the documentation to. If neither this nor -c are provided, the documentation will be printed to standard output.
* `-c, --copy`: Copy the documentaton to the clipboard. If neither this nor -o are provided, the documentation will be printed to standard output
* `--help`: Show the help message and exit.

## `kurisu portal`

Open the Discord Developer Portal.

**Usage**:

```console
$ kurisu portal [OPTIONS] [GATE]:[home|docs|app]
```

**Arguments**:

* `[GATE]:[home|docs|app]`: Where on the developer portal to go. Choose from home (the home page), docs (the documentation), or app (3515.games.dev's application page).  [default: (home)]

**Options**:

* `--help`: Show the help message and exit.

## `kurisu release`

Create a new release. This command is interactive only.

**Usage**:

```console
$ kurisu release [OPTIONS]
```

**Options**:

* `-n, --dry-run`: Run through the release flow without actually pushing a release or making any repository changes.
* `--help`: Show the help message and exit.

## `kurisu settings`

Manage settings configurations.

**Usage**:

```console
$ kurisu settings [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show the help message and exit.

**Commands**:

* [`new`](#kurisu-settings-new): Create a new settings configuration.
* [`sync`](#kurisu-settings-sync): Remove settings configurations that lack a corresponding Doppler configuration.

### `kurisu settings new`

Create a new settings configuration.

**Usage**:

```console
$ kurisu settings new [OPTIONS]
```

**Options**:

* `-c, --config TEXT`: The name of the Doppler configuration to create a settings configuration for. You'll be prompted for this if you don't provide it.
* `-d, --description TEXT`: The description for the new settings configuration. You'll be prompted for this if you don't provide it.
* `--help`: Show the help message and exit.

### `kurisu settings sync`

Remove settings configurations that lack a corresponding Doppler configuration.

**Usage**:

```console
$ kurisu settings sync [OPTIONS]
```

**Options**:

* `--help`: Show the help message and exit.
