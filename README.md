# Cygma Themes

Three coordinated colour themes for creative tools, editors and terminals.

[Preview the themes](https://cygma-audio.github.io/cygma-themes/) · [Source on GitHub](https://github.com/cygma-audio/cygma-themes)

| Theme | Appearance | Character |
| --- | --- | --- |
| Ember | Dark | Warm graphite, apricot signals, soft ivory text |
| Porcelain | Light | Warm paper, umber text, burnt orange |
| Nocturne | Dark alternative | Violet ink, mint signals, lavender detail |

## Install

Download and extract [the complete collection](https://cygma-audio.github.io/cygma-themes/downloads/cygma-themes.zip), then open a terminal in its directory. Requires Python 3.10 or newer. Preview destinations before installing:

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
- Tessel: exported theme data for integration into the app.

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

For browser checks, package the site first, then run `node scripts/test-site.mjs` with Node 22+ and an installed Chromium-family browser (set `CYGMA_BROWSER` if it is outside the detected locations). It serves `dist/` beneath `/cygma-themes/` to match GitHub Pages and checks downloads, assets, real text contrast, keyboard tabs, clipboard, persistence and narrow layouts. Screenshots and the computed contrast report go into `.site-preview/`.

## GitHub Pages deployment

The showcase is published at [cygma-audio.github.io/cygma-themes](https://cygma-audio.github.io/cygma-themes/). The [deployment workflow](https://github.com/cygma-audio/cygma-themes/blob/main/.github/workflows/pages.yml) verifies generated themes and contrast, runs the installer and token tests, packages the download archive, and publishes `dist/` on every push to `main`.

In [repository settings](https://github.com/cygma-audio/cygma-themes/settings/pages), set **Pages → Build and deployment → Source** to **GitHub Actions**. To redeploy without a commit, open [Actions](https://github.com/cygma-audio/cygma-themes/actions/workflows/pages.yml), choose **Run workflow**, and select `main`. Deployment is restricted to `main` and uses the `github-pages` environment.

Edit the website in `site/`, then run `python scripts/package.py` to preview the packaged result locally. `dist/` and the ZIP archives are generated during deployment and do not need to be committed. Website assets and downloads use relative paths so they work beneath `/cygma-themes/`.

## Licensing

Code, palette and theme ports: MIT. Bundled Inter: SIL Open Font License, included beside the font. Cygma Audio brand marks remain brand identifiers; do not present modified or third-party software as an official Cygma product.
