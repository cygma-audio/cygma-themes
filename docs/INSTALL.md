# Install Cygma themes

The installer needs **Python 3.10 or newer** and uses only its standard library. It copies the checked-in theme files, requires no administrator rights, and makes no network requests. It does not activate a theme or edit your application settings.

Run commands from the repository directory. Choose applications explicitly; all three variants are installed unless you select a variant.

The editor extensions declare VS Code API compatibility with **1.80 or newer** (and corresponding VSCodium versions). The Alacritty activation example uses the `[general]` import layout documented for **0.14 or newer**; the exported color files use TOML. See the [Alacritty 0.14 configuration reference](https://alacritty.org/releases/0.14.0/config-alacritty.html). These are format requirements; installation tests validate the files and filesystem operations without launching the applications.

## Linux

```bash
# Preview the exact destinations without writing any files.
bash scripts/install.sh --app vscode --app kitty --dry-run

# Install Ember, Porcelain, and Nocturne for these applications.
bash scripts/install.sh --app vscode --app kitty

# Install one variant for an application.
bash scripts/install.sh --app neovim --variant porcelain
```

## Windows

```powershell
# Preview first.
.\scripts\install.ps1 --app vscode --app windows-terminal --dry-run

# Install the selected application themes.
.\scripts\install.ps1 --app vscode --app windows-terminal

# Python can also be invoked directly; no PowerShell policy change is needed.
py -3 scripts/install.py --app alacritty --variant nocturne
```

## Options

| Option | Meaning |
| --- | --- |
| `--app APP` | Required; repeat to choose applications. |
| `--app all` | Install for every supported application on the current OS, including the optional GTK files on Linux. |
| `--variant NAME` | `ember`, `porcelain`, `nocturne`, or `all`; repeat to select more than one. Default: `all`. |
| `--dry-run` | Print the complete plan, including backups and manifest, without creating directories or writing files. |
| `--uninstall` | Remove tracked files or restore their previous contents. |
| `--target-root PATH` | Place all destinations and state inside an isolated directory; ignore real user configuration environment variables. |
| `--platform linux\|windows` | Test the selected OS layout. Requires `--target-root`. |

Supported application names: `vscode`, `vscodium`, `windows-terminal`, `kitty`, `alacritty`, `wezterm`, `neovim`, and `gtk`. Windows Terminal is Windows-only. The kitty and GTK installers are Linux-only. Unsupported explicit app requests fail; `all` selects only the current OS's supported apps. Run the Linux installer inside a Linux environment such as WSL to install Linux applications there.

## Destinations

`NAME` below is `ember`, `porcelain`, or `nocturne`. Linux paths honor absolute `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, and `XDG_STATE_HOME` values. kitty also honors `KITTY_CONFIG_DIRECTORY`; Neovim honors `XDG_CONFIG_HOME` and a simple directory name in `NVIM_APPNAME` on both systems.

| Application | Linux default | Windows default |
| --- | --- | --- |
| VS Code | `~/.vscode/extensions/cygma-audio.cygma-NAME/` | `%USERPROFILE%\.vscode\extensions\cygma-audio.cygma-NAME\` |
| VSCodium | `~/.vscode-oss/extensions/cygma-audio.cygma-NAME/` | `%USERPROFILE%\.vscode-oss\extensions\cygma-audio.cygma-NAME\` |
| Windows Terminal | — | `%LOCALAPPDATA%\Microsoft\Windows Terminal\Fragments\Cygma\cygma-NAME.json` |
| kitty | `~/.config/kitty/themes/cygma-NAME.conf` | — |
| Alacritty | `~/.config/alacritty/themes/cygma-NAME.toml` | `%APPDATA%\alacritty\themes\cygma-NAME.toml` |
| WezTerm | `~/.config/wezterm/colors/cygma-NAME.toml` | `%LOCALAPPDATA%\Cygma\wezterm\colors\cygma-NAME.toml` |
| Neovim | `~/.config/nvim/colors/cygma_NAME.lua` | `%LOCALAPPDATA%\nvim\colors\cygma_NAME.lua` |
| GTK 3 / 4 (optional) | `~/.local/share/themes/cygma-NAME/gtk-{3.0,4.0}/gtk.css` | — |

VS Code and VSCodium receive one local extension directory per selected variant, with a filtered `package.json`. Restart the editor to discover them. The installer uses the standard desktop extension directory; portable editions, remote servers, and custom `--extensions-dir`/`VSCODE_EXTENSIONS` locations need a manual copy of `ports/vscode` instead. See the official [VS Code extension locations](https://code.visualstudio.com/docs/configure/extensions/extension-marketplace) and [VSCodium migration guide](https://github.com/VSCodium/vscodium/blob/master/docs/migration.md).

Windows Terminal receives one [JSON fragment](https://learn.microsoft.com/en-us/windows/terminal/json-fragment-extensions) per variant. Existing `settings.json` files are untouched.

WezTerm's documented automatic lookup on Windows is beside `wezterm.exe`. This installer uses a user-owned directory, so add that directory to `color_scheme_dirs` manually as shown below. See [WezTerm color scheme discovery](https://wezterm.org/config/appearance.html). The other destinations follow [kitty configuration lookup](https://sw.kovidgoyal.net/kitty/invocation.html), [Alacritty configuration locations](https://alacritty.org/config-alacritty.html), [Neovim standard paths](https://neovim.io/doc/user/starting/#standard-path), and [GTK theme lookup](https://docs.gtk.org/gtk4/class.CssProvider.html).

## Select a theme manually

### VS Code / VSCodium

Restart the editor. Open **Preferences: Color Theme** from the command palette and select **Cygma Ember**, **Cygma Porcelain**, or **Cygma Nocturne**.

### Windows Terminal

Restart Terminal, then choose the scheme in **Settings → Profiles → Defaults → Appearance → Color scheme**, or select it for a specific profile.

### kitty

Add one line to your `kitty.conf`:

```conf
include themes/cygma-ember.conf
```

### Alacritty

Add the import to your existing `alacritty.toml`. If a `[general]` section or `import` list exists, extend it rather than duplicating it:

```toml
[general]
import = ["themes/cygma-ember.toml"]
```

### WezTerm

In your existing Lua configuration, set:

```lua
config.color_scheme = 'Cygma Ember'
```

On Windows, also add the installer destination to your existing `color_scheme_dirs` list:

```lua
config.color_scheme_dirs = {
  os.getenv('LOCALAPPDATA') .. '/Cygma/wezterm/colors',
}
```

If you use a custom configuration location on Linux, include its `colors` directory in `color_scheme_dirs` if WezTerm does not discover the scheme automatically.

### Neovim

Try `:colorscheme cygma_ember`. To keep it, add `vim.cmd.colorscheme('cygma_ember')` to your existing `init.lua`.

### GTK 3 / 4

GTK is an optional application theme: `--app gtk` installs both CSS versions. It does not change desktop settings, overwrite `~/.config/gtk-*/gtk.css`, or recolor every desktop application. Desktop theme controls can select `cygma-ember`, `cygma-porcelain`, or `cygma-nocturne`; application-specific styling and libadwaita may limit the result. To test a compatible GTK application for one launch, use GTK's documented debugging override, for example `GTK_THEME=cygma-ember gtk4-demo` if that demo is installed.

## Uninstall and restore

Use the same app and variant selection. Omit `--variant` to remove every installed Cygma variant for those apps:

```bash
python scripts/install.py --app kitty --variant ember --uninstall --dry-run
python scripts/install.py --app kitty --variant ember --uninstall
```

On Windows, the equivalent is `py -3 scripts/install.py --app windows-terminal --uninstall` or the PowerShell wrapper with the same flags.

The installer records each managed file's app, variant, path, SHA-256 hash, and original-file backup in `manifest.json`. State is stored at `$XDG_STATE_HOME/cygma-themes` (default `~/.local/state/cygma-themes`) on Linux, and `%LOCALAPPDATA%\Cygma\installer` on Windows. Keep this directory until you have finished uninstalling, and use the same configuration environment variables for install and uninstall. Backup snapshots are retained after uninstall; empty theme directories may remain.

An existing file at a Cygma destination is backed up before replacement. Updates preserve that original backup. Uninstall restores its bytes and file mode, or removes the installed file when no original existed. Files untracked by the manifest are left alone. If a tracked file was edited or removed, or a backup fails its hash check, the entire requested operation stops before changing theme files. Save your edits separately and restore the managed file's installed bytes before retrying; there is no force-overwrite option.

Writes use temporary sibling files and atomic replacement. Caught write failures trigger rollback of the requested operation, including its manifest. Symlinks, Windows junctions/reparse points, hardlinked files, manifest path traversal, and concurrent installer locks are rejected. A power interruption or process kill can leave a lock or incomplete operation; retain the manifest and backups for recovery. Remove a stale `.lock` only after verifying no installer is running.

## Test in an isolated directory

These commands never install into real application locations:

```bash
python scripts/install.py --app all --target-root ./install-preview --platform linux --dry-run
python scripts/install.py --app all --target-root ./install-test --platform windows
python scripts/install.py --app all --target-root ./install-test --platform windows --uninstall
python -m unittest discover -s tests -p test_install.py -v
```

The isolated layout uses `PATH/home` as its synthetic home and `PATH/.cygma-state` for installer state. Tests use temporary fixtures, verify both OS layouts, exercise rollback and backup restoration, and invoke the Bash/PowerShell wrappers when available. They never use your application configuration directories.
