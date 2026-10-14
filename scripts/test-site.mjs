/** Dependency-free browser checks. Run: node scripts/test-site.mjs */
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { spawn } from 'node:child_process';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import os from 'node:os';

const root = fileURLToPath(new URL('../', import.meta.url));
const siteRoot = path.join(root, 'dist');
const siteBasePath = '/cygma-themes/';
const artifactRoot = path.join(root, '.site-preview');
const candidates = [process.env.CYGMA_BROWSER, 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', 'C:/Program Files/Google/Chrome/Application/chrome.exe', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome'].filter(Boolean);
const browserPath = candidates.find(existsSync);
assert.ok(browserPath, 'Set CYGMA_BROWSER to a Chromium-family browser executable.');
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.ttf': 'font/ttf', '.zip': 'application/zip' };
const server = createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    if (!pathname.startsWith(siteBasePath)) throw new Error('Outside project path');
    const relative = pathname.slice(siteBasePath.length) || 'index.html';
    const full = path.resolve(siteRoot, relative);
    const resolvedRelative = path.relative(siteRoot, full);
    if (resolvedRelative === '..' || resolvedRelative.startsWith(`..${path.sep}`) || path.isAbsolute(resolvedRelative)) throw new Error('Outside site');
    const body = await readFile(full);
    response.writeHead(200, { 'Content-Type': types[path.extname(full)] || 'application/octet-stream' });
    response.end(body);
  } catch {
    response.writeHead(404);
    response.end('Not found');
  }
});
await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
const siteUrl = `${origin}${siteBasePath}`;
const profileParent = path.resolve(os.tmpdir());
const profile = await mkdtemp(path.join(profileParent, 'cygma-browser-check-'));
let browser;
let socket;
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

try {
  await mkdir(artifactRoot, { recursive: true });
  const html = await readFile(path.join(siteRoot, 'index.html'), 'utf8');
  const localLinks = [...html.matchAll(/(?:href|src)="([^"#][^"]*)"/g)].map((match) => match[1]).filter((href) => !/^(https?:|data:|mailto:)/.test(href));
  const themes = JSON.parse(await readFile(path.join(siteRoot, 'themes.json'), 'utf8'));
  localLinks.push('themes.json');
  for (const name of Object.keys(themes.themes)) localLinks.push(`downloads/${name}.tokens.json`);
  for (const href of new Set(localLinks)) {
    const url = new URL(href, siteUrl);
    assert.equal(url.origin, origin, `${href}: local resource stays on this site`);
    assert.ok(url.pathname.startsWith(siteBasePath), `${href}: resolves beneath the GitHub Pages project path`);
    const relative = decodeURIComponent(url.pathname.slice(siteBasePath.length)) || 'index.html';
    const expected = await readFile(path.resolve(siteRoot, relative));
    const response = await fetch(url);
    assert.equal(response.status, 200, `${href}: generated resource is served successfully`);
    assert.equal(response.headers.get('content-type'), types[path.extname(relative)] || 'application/octet-stream', `${href}: correct resource type`);
    assert.deepEqual(Buffer.from(await response.arrayBuffer()), expected, `${href}: served bytes match dist`);
  }
  for (const pathname of ['/', '/index.html', '/cygma-themes-other/index.html', '/cygma-themes/%2e%2e/README.md', '/cygma-themes/..%2fREADME.md', '/cygma-themes/..%5cREADME.md']) {
    assert.equal((await fetch(`${origin}${pathname}`)).status, 404, `${pathname}: requests outside the generated project site are rejected`);
  }

  browser = spawn(browserPath, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-features=msEdgeSidebarV2', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { windowsHide: true, stdio: 'ignore' });
  let endpoint;
  for (let attempt = 0; attempt < 100; attempt++) {
    try {
      const activePort = await readFile(path.join(profile, 'DevToolsActivePort'), 'utf8');
      const [port, route] = activePort.trim().split(/\r?\n/);
      endpoint = `ws://127.0.0.1:${port}${route}`;
      break;
    } catch { await pause(100); }
  }
  assert.ok(endpoint, 'Browser debugging endpoint started');
  socket = new WebSocket(endpoint);
  await new Promise((resolve, reject) => { socket.addEventListener('open', resolve, { once: true }); socket.addEventListener('error', reject, { once: true }); });
  let requestId = 0;
  const pending = new Map();
  const pageErrors = [];
  const resourceErrors = [];
  const resourceRequests = new Map();
  socket.addEventListener('message', ({ data }) => {
    const message = JSON.parse(data);
    if (message.method === 'Runtime.exceptionThrown') pageErrors.push(message.params.exceptionDetails.text);
    if (message.method === 'Network.requestWillBeSent') resourceRequests.set(message.params.requestId, message.params.request.url);
    if (message.method === 'Network.responseReceived' && message.params.response.status >= 400) {
      resourceErrors.push(`${message.params.response.status} ${message.params.response.url}`);
    }
    if (message.method === 'Network.loadingFailed' && !message.params.canceled) {
      resourceErrors.push(`${message.params.errorText} ${resourceRequests.get(message.params.requestId) || message.params.requestId}`);
    }
    if (pending.has(message.id)) {
      const { resolve, reject, timer } = pending.get(message.id);
      pending.delete(message.id);
      clearTimeout(timer);
      if (message.error) reject(new Error(JSON.stringify(message.error)));
      else resolve(message.result);
    }
  });
  function send(method, params = {}, sessionId) {
    return new Promise((resolve, reject) => {
      const id = ++requestId;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`${method} timed out`)); }, 15000);
      pending.set(id, { resolve, reject, timer });
      socket.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
    });
  }
  const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
  const cdp = (method, params) => send(method, params, sessionId);
  const evaluate = async (expression) => {
    const result = await cdp('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    assert.ok(!result.exceptionDetails, `Browser expression failed: ${result.exceptionDetails?.text}`);
    return result.result.value;
  };
  const contrastAudit = `(() => {
    const rgba = value => { const channels = value.match(/[\\d.]+/g).map(Number); return [...channels.slice(0, 3), channels[3] ?? 1]; };
    const over = (top, below) => { const a = top[3] + below[3] * (1 - top[3]); return a ? [0, 1, 2].map(i => (top[i] * top[3] + below[i] * below[3] * (1 - top[3])) / a).concat(a) : [0, 0, 0, 0]; };
    const luminosity = color => color.slice(0, 3).map(x => x / 255).map(x => x <= .04045 ? x / 12.92 : ((x + .055) / 1.055) ** 2.4).reduce((sum, x, i) => sum + x * [.2126, .7152, .0722][i], 0);
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const failures = []; let count = 0; let minimum = 99;
    while (walker.nextNode()) {
      const node = walker.currentNode; const el = node.parentElement;
      if (!node.textContent.trim() || el.closest('script,style,noscript,svg,option,.visually-hidden,.toast,.skip-link')) continue;
      const range = document.createRange(); range.selectNodeContents(node);
      if (!range.getBoundingClientRect().height) continue;
      let current = el; let visible = true; let foreground = rgba(getComputedStyle(el).color); let background = [0, 0, 0, 0];
      if (foreground[3] === 0) continue;
      while (current) {
        const style = getComputedStyle(current);
        if (style.visibility === 'hidden' || style.display === 'none' || Number(style.opacity) === 0) { visible = false; break; }
        const surface = rgba(style.backgroundColor);
        foreground = over(foreground, surface); background = over(background, surface);
        foreground[3] *= Number(style.opacity); background[3] *= Number(style.opacity);
        current = current.parentElement;
      }
      if (!visible) continue;
      foreground = over(foreground, [255,255,255,1]); background = over(background, [255,255,255,1]);
      const l1 = luminosity(foreground); const l2 = luminosity(background);
      const ratio = (Math.max(l1,l2) + .05) / (Math.min(l1,l2) + .05);
      count++; minimum = Math.min(minimum, ratio);
      if (ratio < 4.5) failures.push({ text: node.textContent.trim().slice(0,80), ratio: Number(ratio.toFixed(3)), element: el.className, foreground, background });
    }
    return { count, minimum, failures };
  })()`;
  await cdp('Runtime.enable');
  await cdp('Network.enable');
  await cdp('Page.enable');
  await cdp('DOM.enable');
  await cdp('CSS.enable');
  await cdp('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1050, deviceScaleFactor: 1, mobile: false });
  await send('Browser.grantPermissions', { origin, permissions: ['clipboardReadWrite', 'clipboardSanitizedWrite'] });
  await cdp('Page.navigate', { url: siteUrl });
  await evaluate(`new Promise((resolve, reject) => { let n = 0; const t = setInterval(() => { if (document.querySelectorAll('.swatch').length === 16 && document.fonts.status === 'loaded') { clearInterval(t); resolve(true); } else if (++n > 100) { clearInterval(t); reject(new Error('Palette failed to load')); } }, 50); })`);
  assert.equal(await evaluate(`document.documentElement.dataset.theme`), 'ember');
  assert.equal(await evaluate(`location.pathname`), siteBasePath, 'Generated site loads at the GitHub Pages project path');
  for (const href of await evaluate(`Array.from(document.querySelectorAll('a[download]'), link => link.href)`)) {
    assert.ok(href.startsWith(siteUrl), `${href}: browser download link retains the project path`);
  }

  const contrastResults = [];
  for (const [name, theme] of Object.entries(themes.themes)) {
    await evaluate(`document.querySelector('[data-flavour="${name}"]').click()`);
    assert.equal(await evaluate(`document.documentElement.dataset.theme`), name);
    assert.equal(await evaluate(`document.querySelectorAll('[data-flavour][aria-pressed="true"]').length`), 1);
    assert.equal(await evaluate(`getComputedStyle(document.documentElement).getPropertyValue('--surface-canvas').trim().toUpperCase()`), theme.tokens['surface.canvas'].toUpperCase());
    assert.equal(await evaluate(`document.querySelector('.swatch-label code').textContent`), theme.tokens['surface.canvas']);
    assert.equal(await evaluate(`document.querySelector('.token-download').href`), `${siteUrl}downloads/${name}.tokens.json`, `${name}: token download retains the project path`);
    assert.ok((await evaluate(`document.querySelector('.install-command').textContent`)).endsWith(`--variant ${name}`));
    for (const tab of ['code', 'terminal', 'interface']) {
      await evaluate(`document.getElementById('tab-${tab}').click()`);
      await pause(200);
      const audit = await evaluate(contrastAudit);
      contrastResults.push({ flavour: name, preview: tab, state: 'default', ...audit });
      assert.deepEqual(audit.failures, [], `${name}/${tab}: visible text meets 4.5:1 against rendered backgrounds`);
    }
    const { root: domRoot } = await cdp('DOM.getDocument');
    const { nodeIds } = await cdp('DOM.querySelectorAll', { nodeId: domRoot.nodeId, selector: 'button,a,select' });
    for (const nodeId of nodeIds) await cdp('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: ['hover', 'focus-visible'] });
    await pause(200);
    const hoverAudit = await evaluate(contrastAudit);
    contrastResults.push({ flavour: name, preview: 'interface', state: 'hover/focus', ...hoverAudit });
    assert.deepEqual(hoverAudit.failures, [], `${name}: hovered/focused text meets 4.5:1`);
    for (const nodeId of nodeIds) await cdp('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [] });
  }
  await writeFile(path.join(artifactRoot, 'browser-contrast.json'), JSON.stringify(contrastResults, null, 2));
  await evaluate(`document.querySelector('[data-flavour="porcelain"]').click()`);
  await cdp('Page.reload');
  await evaluate(`new Promise(resolve => { const t = setInterval(() => { if (document.querySelectorAll('.swatch').length === 16) { clearInterval(t); resolve(true); } }, 30); })`);
  assert.equal(await evaluate(`document.documentElement.dataset.theme`), 'porcelain', 'Flavour persists across reloads');
  await evaluate(`document.querySelector('.swatch').click()`);
  await pause(150);
  assert.equal(await evaluate(`navigator.clipboard.readText()`), themes.themes.porcelain.tokens['surface.canvas'], 'Swatches copy exact hex values');

  await evaluate(`document.getElementById('tab-code').focus()`);
  await cdp('Input.dispatchKeyEvent', { type: 'keyDown', key: 'ArrowRight', code: 'ArrowRight', windowsVirtualKeyCode: 39 });
  assert.equal(await evaluate(`document.activeElement.id`), 'tab-terminal');
  assert.equal(await evaluate(`document.getElementById('preview-terminal').hidden`), false);
  await cdp('Input.dispatchKeyEvent', { type: 'keyDown', key: 'End', code: 'End', windowsVirtualKeyCode: 35 });
  assert.equal(await evaluate(`document.activeElement.id`), 'tab-interface');
  assert.equal(await evaluate(`document.querySelectorAll('[role="tabpanel"]:not([hidden])').length`), 1);

  for (const platform of ['windows', 'linux']) {
    await evaluate(`document.getElementById('platform').value='${platform}'; document.getElementById('platform').dispatchEvent(new Event('change'));`);
    assert.equal(await evaluate(`document.querySelectorAll('.install-card').length`), 8);
    assert.equal(await evaluate(`document.querySelectorAll('.install-command').length`), platform === 'windows' ? 6 : 7);
    assert.ok(await evaluate(`Array.from(document.querySelectorAll('.install-command')).every(item => item.textContent.includes('--app ') && item.textContent.includes('--variant porcelain'))`));
    await evaluate(`document.querySelector('.copy-command').click()`);
    await pause(100);
    assert.equal(await evaluate(`navigator.clipboard.readText()`), await evaluate(`document.querySelector('.install-command').textContent`), 'Installer command copies exactly');
  }
  assert.ok(await evaluate(`Array.from(document.querySelectorAll('.install-card-activation')).some(item => item.textContent.includes('colorscheme cygma_porcelain'))`));

  await evaluate(`document.querySelector('[data-flavour="ember"]').click(); document.getElementById('tab-code').click(); document.activeElement.blur(); document.getElementById('toast').classList.remove('visible'); window.scrollTo(0,0);`);
  await pause(250);
  assert.ok(await evaluate(`document.querySelector('.active-code-line').getBoundingClientRect().bottom <= document.querySelector('.code-lines').getBoundingClientRect().bottom`), 'All code lines are visible in the preview');
  const desktopShot = await cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
  await writeFile(path.join(artifactRoot, 'desktop.png'), Buffer.from(desktopShot.data, 'base64'));
  const layout = await cdp('Page.getLayoutMetrics');
  const fullShot = await cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: 0, y: 0, width: 1440, height: layout.cssContentSize.height, scale: 1 } });
  await writeFile(path.join(artifactRoot, 'full-page.png'), Buffer.from(fullShot.data, 'base64'));
  for (const width of [390, 320]) {
    await cdp('Emulation.setDeviceMetricsOverride', { width, height: 844, deviceScaleFactor: 1, mobile: true });
    assert.ok(await evaluate(`document.documentElement.scrollWidth <= document.documentElement.clientWidth`), `No page overflow at ${width}px`);
    for (const tab of ['code', 'terminal', 'interface']) {
      await evaluate(`document.getElementById('tab-${tab}').click()`);
      assert.ok(await evaluate(`document.documentElement.scrollWidth <= document.documentElement.clientWidth`), `No ${tab} overflow at ${width}px`);
    }
    if (width === 390) {
      await evaluate(`document.getElementById('tab-code').click(); window.scrollTo(0,0)`);
      const mobileShot = await cdp('Page.captureScreenshot', { format: 'png', captureBeyondViewport: false });
      await writeFile(path.join(artifactRoot, 'mobile.png'), Buffer.from(mobileShot.data, 'base64'));
    }
  }
  assert.deepEqual(pageErrors, [], 'No uncaught browser errors');
  assert.deepEqual(resourceErrors, [], 'No failed browser resource requests');
  const requestedPaths = Array.from(resourceRequests.values()).filter(url => new URL(url).origin === origin).map(url => new URL(url).pathname);
  assert.ok(requestedPaths.every(pathname => pathname.startsWith(siteBasePath)), 'Browser resource requests retain the GitHub Pages project path');
  for (const relative of ['index.html', 'app.js', 'style.css', 'tokens.css', 'themes.json', 'assets/Inter.ttf']) {
    assert.ok(requestedPaths.includes(`${siteBasePath}${relative === 'index.html' ? '' : relative}`), `${relative}: generated resource was requested by the browser`);
  }
  console.log('PASS: generated dist site at /cygma-themes/, project-relative downloads/assets and served bytes, server path boundaries, generated palette values, all 3 flavours, rendered text contrast >=4.5:1 (3 previews + hover/focus), persistence, keyboard tabs, clipboard, 8 app cards, 2 OS command sets, 390px/320px layouts, no runtime or resource errors.');
  console.log(`Screenshots: ${artifactRoot}`);
  await send('Browser.close');
} finally {
  socket?.close();
  browser?.kill();
  await new Promise((resolve) => server.close(resolve));
  // Only remove the exact temporary profile created by this process.
  assert.equal(path.dirname(path.resolve(profile)), profileParent);
  assert.ok(path.basename(profile).startsWith('cygma-browser-check-'));
  await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 150 });
}
