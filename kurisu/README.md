# Kurisu

Kurisu is 3515.games' development command-line interface.

**Usage**:

```console
$ kurisu [OPTIONS] COMMAND [ARGS]...
```

**Options**:

- `--install-completion`: Install completion for the current shell.
- `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
- `--help`: Show the help message and exit.

Kurisu © 2023 celsius narhwal. Thank you kindly for your attention.

**Commands**:

- [`check`](#kurisu-check): Check certain release criteria.
- [`copyright`](#kurisu-copyright): Attach copyright notices to all non-gitignored Python source files.
- [`docs`](#kurisu-docs): Open frequently-used documentation sites.
- [`document`](#kurisu-document): Generate Kurisu's documentation.
- [`invite`](#kurisu-invite): Generate an invite link for 3515.games. By default, this generates an invite link for the development instance.
- [`licenses`](#kurisu-licenses): Generate the Markdown source for https://3515.games/legal/acknowledgements/.
- [`notes`](#kurisu-notes): Generate release notes.
- [`portal`](#kurisu-portal): Open 3515.games.dev on the Discord Developer Portal.
- [`vercel`](#kurisu-vercel): Open the latest preview deploymet of 3515.games' website.

## `kurisu check`

Check certain release criteria.

**Usage**:

```console
$ kurisu check [OPTIONS]
```

**Options**:

- `--help`: Show the help message and exit.

## `kurisu copyright`

Attach copyright notices to all non-gitignored Python source files.

**Usage**:

```console
$ kurisu copyright [OPTIONS]
```

**Options**:

- `-z, --nonzero`: Exit nonzero if files are changed.
- `-v, --verbose`: Show the name of each changed file.
- `-q, --quiet`: Suppress all output aside from errors. Overrides -v.
- `-n, --dry-run`: Run as usual but without actually changing any files.
- `--help`: Show the help message and exit.

## `kurisu docs`

Open frequently-used documentation sites.

**Usage**:

```console
$ kurisu docs [OPTIONS] SITE:{attrs|discord|fontawesome|material|icons|numpydoc|pycord|pydantic}
```

**Arguments**:

- `SITE:{attrs|discord|fontawesome|material|icons|numpydoc|pycord|pydantic}`: The documentation site to open. [required]

**Options**:

- `--help`: Show the help message and exit.

## `kurisu document`

Generate Kurisu's documentation.

**Usage**:

```console
$ kurisu document [OPTIONS]
```

**Options**:

- `--output FILE`: The file to write the documentation to. Defaults to kurisu/README.md.
- `-o, --override`: Override the the file specified by --output if it already exists. If the file exists and you don't pass this option, you'll be asked if you want to override it.
- `-c, --copy`: Copy the documentation to the clipboard.
- `--help`: Show the help message and exit.

## `kurisu invite`

Generate an invite link for 3515.games. By default, this generates an invite link for the development instance.

**Usage**:

```console
$ kurisu invite [OPTIONS]
```

**Options**:

- `-p, --production`: Generate an invite link for the production instance of 3515.games.
- `-c, --copy`: Copy the invite link to the clipboard.
- `-o, --open`: Open the invite link in a web browser.
- `--help`: Show the help message and exit.

## `kurisu licenses`

Generate the Markdown source for https://3515.games/legal/acknowledgements/.

**Usage**:

```console
$ kurisu licenses [OPTIONS]
```

**Options**:

- `--help`: Show the help message and exit.

## `kurisu notes`

Generate release notes.

**Usage**:

```console
$ kurisu notes [OPTIONS]
```

**Options**:

- `--help`: Show the help message and exit.

## `kurisu portal`

Open 3515.games.dev on the Discord Developer Portal.

**Usage**:

```console
$ kurisu portal [OPTIONS]
```

**Options**:

- `--help`: Show the help message and exit.

## `kurisu vercel`

Open the latest preview deploymet of 3515.games' website.

**Usage**:

```console
$ kurisu vercel [OPTIONS]
```

**Options**:

- `--help`: Show the help message and exit.
