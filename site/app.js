'use strict';

(() => {
  const flavourNames = ['ember', 'porcelain', 'nocturne'];
  const essentialRoles = [
    ['Canvas', 'surface.canvas'], ['Panel', 'surface.panel'],
    ['Text', 'text.primary'], ['Accent', 'action.primary'],
    ['String', 'syntax.string'], ['Function', 'syntax.function'],
    ['Type', 'syntax.type'], ['Keyword', 'syntax.keyword'],
    ['Comment', 'syntax.comment'], ['Number', 'syntax.number'],
    ['Success', 'state.success'], ['Warning', 'state.warning'],
    ['Error', 'state.error'], ['Info', 'state.info'],
    ['Selection', 'surface.selection'], ['Focus', 'border.focus']
  ];
  const apps = [
    { id: 'vscode', name: 'VS Code', icon: '⌁', kind: 'EDITOR', platforms: ['windows', 'linux'], description: 'A complete colour theme for the editor, syntax and workbench.', activate: 'Restart the editor. Open Preferences: Color Theme and choose Cygma {name}.' },
    { id: 'vscodium', name: 'VSCodium', icon: '⌁', kind: 'EDITOR', platforms: ['windows', 'linux'], description: 'The same considered workbench and syntax colours for VSCodium.', activate: 'Restart the editor. Open Preferences: Color Theme and choose Cygma {name}.' },
    { id: 'windows-terminal', name: 'Windows Terminal', icon: '>_', kind: 'TERMINAL', platforms: ['windows'], description: 'A matching sixteen-colour palette for your Windows command line.', activate: 'In Settings → Profiles → Appearance, select the Cygma {name} colour scheme.' },
    { id: 'kitty', name: 'Kitty', icon: '↳', kind: 'TERMINAL', platforms: ['linux'], description: 'Warm neutrals, clear ANSI colours and a cursor that belongs.', activate: 'Add include themes/cygma-{slug}.conf to kitty.conf, then reload Kitty.' },
    { id: 'alacritty', name: 'Alacritty', icon: 'Λ', kind: 'TERMINAL', platforms: ['windows', 'linux'], description: 'A focused terminal palette, ready for your Alacritty configuration.', activate: 'Add themes/cygma-{slug}.toml to your Alacritty general.import list. See the collection’s installation guide for full paths.' },
    { id: 'wezterm', name: 'WezTerm', icon: '≋', kind: 'TERMINAL', platforms: ['windows', 'linux'], description: 'A shared colour language for every pane and tab.', activate: 'Set color_scheme to “Cygma {name}” in your WezTerm configuration.' },
    { id: 'neovim', name: 'Neovim', icon: 'N', kind: 'EDITOR', platforms: ['windows', 'linux'], description: 'Syntax, diagnostics and interface highlights for your Neovim setup.', activate: 'Enable termguicolors and set colorscheme cygma_{slug}.' },
    { id: 'gtk', name: 'GTK 3 / 4', icon: '▦', kind: 'DESKTOP', platforms: ['linux'], description: 'Bring the palette to compatible GTK applications on your Linux desktop.', activate: 'Select cygma-{slug} in your desktop’s GTK theme settings. See the collection’s GTK compatibility notes.' }
  ];

  let currentFlavour = 'ember';
  let themeData;
  let toastTimer;
  const byId = (id) => document.getElementById(id);

  function announce(message) {
    const toast = byId('toast');
    toast.textContent = message;
    toast.classList.add('visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('visible'), 3200);
  }

  async function copyText(value, label) {
    try {
      if (!navigator.clipboard || !window.isSecureContext) throw new Error('Clipboard API unavailable');
      await navigator.clipboard.writeText(value);
      announce(`${label} copied`);
    } catch {
      const previousFocus = document.activeElement;
      const field = document.createElement('textarea');
      field.value = value;
      field.setAttribute('readonly', '');
      field.style.position = 'fixed';
      field.style.top = '-1000px';
      document.body.append(field);
      field.select();
      let copied = false;
      try { copied = document.execCommand('copy'); } catch { /* The visible value remains available to select. */ }
      field.remove();
      previousFocus?.focus({ preventScroll: true });
      announce(copied ? `${label} copied` : `Copy unavailable. Select and copy the displayed ${label === 'Command' ? 'command' : 'hex value'}.`);
    }
  }

  function readableInk(hex) {
    const channels = hex.replace('#', '').match(/.{2}/g).map((channel) => parseInt(channel, 16) / 255);
    const linear = channels.map((channel) => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4);
    return linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722 > 0.179 ? '#111111' : '#ffffff';
  }

  function renderPalette() {
    if (!themeData) return;
    const tokens = themeData.themes[currentFlavour].tokens;
    const grid = byId('swatches');
    grid.replaceChildren();
    essentialRoles.forEach(([label, role]) => {
      const hex = tokens[role];
      if (!/^#[0-9a-f]{6}$/i.test(hex)) return;
      const button = document.createElement('button');
      button.className = 'swatch';
      button.type = 'button';
      button.setAttribute('aria-label', `Copy ${label}, ${hex}`);
      button.title = `${role}: ${hex}`;
      const color = document.createElement('span');
      color.className = 'swatch-color';
      color.style.backgroundColor = hex;
      color.style.color = readableInk(hex);
      color.setAttribute('aria-hidden', 'true');
      const copyIcon = document.createElement('span');
      copyIcon.className = 'swatch-copy';
      copyIcon.textContent = '⧉';
      color.append(copyIcon);
      const caption = document.createElement('span');
      caption.className = 'swatch-label';
      const name = document.createElement('strong');
      name.textContent = label;
      const value = document.createElement('code');
      value.textContent = hex;
      caption.append(name, value);
      button.append(color, caption);
      button.addEventListener('click', () => copyText(hex, hex.toUpperCase()));
      grid.append(button);
    });
  }

  function installCommand(app, platform, flavour) {
    return platform === 'windows'
      ? `.\\scripts\\install.ps1 --app ${app} --variant ${flavour}`
      : `python3 scripts/install.py --app ${app} --variant ${flavour}`;
  }

  function renderInstallers() {
    const platform = byId('platform').value;
    const grid = byId('install-grid');
    const name = currentFlavour[0].toUpperCase() + currentFlavour.slice(1);
    grid.replaceChildren();
    apps.forEach((app) => {
      const card = document.createElement('article');
      card.className = 'install-card';
      const heading = document.createElement('div');
      heading.className = 'install-card-top';
      const icon = document.createElement('span');
      icon.className = 'app-icon';
      icon.setAttribute('aria-hidden', 'true');
      icon.textContent = app.icon;
      const title = document.createElement('h3');
      title.textContent = app.name;
      const kind = document.createElement('span');
      kind.className = 'app-kind';
      kind.textContent = app.kind;
      heading.append(icon, title, kind);
      const description = document.createElement('p');
      description.className = 'install-card-description';
      description.textContent = app.description;
      card.append(heading, description);
      if (app.platforms.includes(platform)) {
        const command = installCommand(app.id, platform, currentFlavour);
        const row = document.createElement('div');
        row.className = 'command-row';
        const code = document.createElement('code');
        code.className = 'install-command';
        code.textContent = command;
        const copy = document.createElement('button');
        copy.className = 'copy-command';
        copy.type = 'button';
        copy.textContent = 'Copy';
        copy.setAttribute('aria-label', `Copy ${app.name} installation command`);
        copy.addEventListener('click', () => copyText(command, 'Command'));
        row.append(code, copy);
        const activation = document.createElement('p');
        activation.className = 'install-card-activation';
        const label = document.createElement('strong');
        label.textContent = 'Then: ';
        const activationText = app.id === 'wezterm' && platform === 'windows'
          ? 'Add the installed LOCALAPPDATA/Cygma/wezterm/colors directory to color_scheme_dirs, then set color_scheme to “Cygma {name}”. See the included installation guide for the Lua snippet.'
          : app.activate;
        activation.append(label, activationText.replaceAll('{name}', name).replaceAll('{slug}', currentFlavour));
        card.append(row, activation);
      } else {
        const unavailable = document.createElement('p');
        unavailable.className = 'unavailable-message';
        unavailable.textContent = `Available on ${app.platforms.map((item) => ({ windows: 'Windows', linux: 'Linux' })[item]).join(' and ')}. Switch the operating system above to see the command.`;
        card.append(unavailable);
      }
      grid.append(card);
    });
    byId('platform-note').textContent = platform === 'linux'
      ? 'GTK support varies by application. Libadwaita applications and desktop shells may use their own styling; see the collection’s compatibility notes.'
      : 'Run commands from PowerShell. If your execution policy blocks a script, use: py -3 scripts/install.py --app APP --variant FLAVOUR, replacing APP and FLAVOUR with the values above.';
  }

  function selectFlavour(flavour, announceChange = true) {
    if (!flavourNames.includes(flavour)) return;
    currentFlavour = flavour;
    const name = flavour[0].toUpperCase() + flavour.slice(1);
    document.documentElement.dataset.theme = flavour;
    document.querySelectorAll('[data-flavour]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.flavour === flavour)));
    document.querySelectorAll('[data-current-name]').forEach((node) => { node.textContent = name; });
    document.querySelectorAll('[data-current-slug]').forEach((node) => { node.textContent = flavour; });
    document.querySelectorAll('.token-download').forEach((link) => { link.href = `downloads/${flavour}.tokens.json`; });
    if (themeData) {
      document.querySelector('meta[name="theme-color"]').content = themeData.themes[flavour].tokens['surface.canvas'];
    }
    try { localStorage.setItem('cygma-flavour', flavour); } catch { /* Storage is optional. */ }
    renderPalette();
    renderInstallers();
    if (announceChange) byId('theme-status').textContent = `${name} theme selected. Preview, palette and installation commands updated.`;
  }

  const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
  function selectTab(tab, focus = false) {
    tabs.forEach((item) => {
      const selected = item === tab;
      item.setAttribute('aria-selected', String(selected));
      item.tabIndex = selected ? 0 : -1;
      byId(item.getAttribute('aria-controls')).hidden = !selected;
    });
    if (focus) tab.focus();
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectTab(tab));
    tab.addEventListener('keydown', (event) => {
      let next;
      if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
      if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
      if (event.key === 'Home') next = 0;
      if (event.key === 'End') next = tabs.length - 1;
      if (next !== undefined) { event.preventDefault(); selectTab(tabs[next], true); }
    });
  });
  document.querySelectorAll('[data-flavour]').forEach((button) => button.addEventListener('click', () => selectFlavour(button.dataset.flavour)));
  byId('platform').addEventListener('change', renderInstallers);
  const device = navigator.userAgentData?.platform || navigator.platform || '';
  byId('platform').value = /linux/i.test(device) ? 'linux' : 'windows';
  let savedFlavour;
  try { savedFlavour = localStorage.getItem('cygma-flavour'); } catch { /* Default to Ember when storage is blocked. */ }
  selectFlavour(flavourNames.includes(savedFlavour) ? savedFlavour : 'ember', false);

  fetch('themes.json')
    .then((response) => {
      if (!response.ok) throw new Error('Theme data request failed');
      return response.json();
    })
    .then((data) => {
      if (!flavourNames.every((flavour) => data.themes?.[flavour]?.tokens)) throw new Error('Theme data is incomplete');
      themeData = data;
      const cardRoles = ['surface.canvas', 'surface.raised', 'text.primary', 'action.primary', 'syntax.string', 'syntax.function', 'state.info', 'syntax.type'];
      flavourNames.forEach((flavour) => {
        document.querySelectorAll(`.${flavour}-colours > i`).forEach((swatch, index) => { swatch.style.backgroundColor = data.themes[flavour].tokens[cardRoles[index]]; });
      });
      selectFlavour(currentFlavour, false);
    })
    .catch(() => {
      const message = document.createElement('p');
      message.className = 'loading-message';
      message.textContent = 'The interactive palette could not load. Download the token file above to explore the colours, or reload this page.';
      byId('swatches').replaceChildren(message);
    });
})();
