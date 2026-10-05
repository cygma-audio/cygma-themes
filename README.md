# Cygma Themes

Three coordinated colour themes for creative tools, editors and terminals.

| Theme | Appearance | Character |
| --- | --- | --- |
| Ember | Dark | Warm graphite, apricot signals, soft ivory text |
| Porcelain | Light | Warm paper, umber text, burnt orange |
| Nocturne | Dark alternative | Violet ink, mint signals, lavender detail |

## Install

Download and extract the complete archive, then open a terminal in its directory. Requires Python 3.10 or newer. Preview destinations before installing:

```powershell
# Windows PowerShell
.\scripts\install.ps1 --app vscode --variant ember --dry-run
.\scripts\install.ps1 --app vscode --variant ember
```

```bash
# Linux
bash scripts/install.sh --app vscode --variant ember --dry-run
bash scripts/install.sh --app vscode --variant ember
```

Then use **Preferences: Color Theme → Cygma Ember** in VS Code. Repeat `--app` or `--variant` to select more; omit `--variant` for all three. `--app all` installs files for every supported app on your OS, including apps you may not have installed. Activation remains your choice. The scripts do not replace your editor settings or switch your desktop automatically.

See [installation and removal](docs/INSTALL.md) for native locations, app activation, backups and `--uninstall`.

## Ports

- VS Code and VSCodium: editor, syntax, terminal and workbench themes.
- Windows Terminal: native colour-scheme fragments.
- Kitty, Alacritty and WezTerm: native terminal palettes.
- Neovim: Lua colour schemes and diagnostic highlights.
- GTK 3/4: a small stylesheet for applications that respect GTK themes; not a complete desktop or libadwaita skin.
- Tessel: embedded theme data, accessible through its Cygma theme category after compiling the app.

The installer targets Windows and Linux. The theme files can be adapted to other systems; those installs are not implemented here. These ports have automated format and installer tests, but have not all been visually tested inside their native applications.

## Design tokens and contrast

`tokens/palette-source.json` holds the colour definitions. `scripts/build.py` compiles DTCG-style typed JSON with semantic aliases, CSS variables and native app files. Application code consumes roles such as `text.primary`, `surface.panel`, `action.primary` and `state.error`.

Every named text/background pair in the generated audit meets **4.5:1**; meaningful control/focus boundaries meet **3:1**. Decorative separators are intentionally quieter. This verifies specified opaque pairs, not complete application accessibility or legal compliance. See [contrast scope and usage rules](docs/TOKENS.md) and [the machine-readable report](reports/contrast.json).

## Develop and verify

```bash
python scripts/build.py
python scripts/build.py --check
python -m unittest discover -s tests -v
python scripts/package.py
python -m http.server 8080 --directory dist
```

The package command generates `releases/cygma-themes-0.1.0.zip` and the ready-to-serve `dist/` website. The showcase switches the complete page between flavours, previews code/terminal/interface roles, copies values and provides app-specific installation commands. No analytics or external font service is required.

For browser checks, run `node scripts/test-site.mjs` with Node 22+ and an installed Chromium-family browser (set `CYGMA_BROWSER` if it is outside the detected locations). It checks real text contrast, keyboard tabs, clipboard, persistence and narrow layouts. Screenshots and the computed contrast report go into `.site-preview/`.

## Licensing

Code, palette and theme ports: MIT. Bundled Inter: SIL Open Font License, included beside the font. Cygma Audio brand marks remain brand identifiers; do not present modified or third-party software as an official Cygma product.
