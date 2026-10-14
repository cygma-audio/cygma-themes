# Tokens, contrast and rendering

## Contract

The palette compiler uses the [Design Tokens Community Group format](https://www.designtokens.org/tr/2025.10/format/) and its [sRGB colour representation](https://www.designtokens.org/tr/2025.10/color/): inherited `$type: "color"`, typed `$value` objects and semantic aliases such as `{base.accent}`. Native exports resolve aliases into app-specific values. Edit the source palette, regenerate and run the tests; do not manually edit generated exports.

| Role family | Use |
| --- | --- |
| `surface.*` | Opaque backgrounds, containers and selection |
| `text.*` | Primary, secondary, muted and inverse labels |
| `action.*` | Primary button fill and its paired label |
| `border.control`, `border.focus` | Meaningful edges and visible focus cues |
| `border.subtle` | Decorative separators only |
| `state.*` | Error, warning, success and information, paired with words/icons |
| `syntax.*` | Code token categories |
| `terminal.ansi0..15` | Terminal text colours on the documented surfaces |

Use `action.onPrimary` on a filled `action.primary` control. Use ordinary text roles on surface roles. Inverse text is not intended for ordinary panels. Theme switching should replace all roles in one operation, not fade through untested intermediate colours.

## Measured requirements

[WCAG 2.2 text contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) requires 4.5:1 for ordinary text and 3:1 for qualifying large text. This project uses 4.5:1 even for large text. [Non-text contrast](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html) requires 3:1 for the visual information needed to identify controls and states. Decorative borders are not required to meet that threshold.

For each sRGB channel `c` scaled to 0–1, linearize with `c / 12.92` for `c <= 0.04045`, otherwise `((c + 0.055) / 1.055)^2.4`. Relative luminance is `0.2126 R + 0.7152 G + 0.0722 B`; contrast is `(lighter + 0.05) / (darker + 0.05)`. Tests compare unrounded values to the thresholds.

The report covers primary/secondary/muted/selected text, accents, syntax, semantic states and all ANSI slots on canvas, panel, raised, hover and selection surfaces. It also covers primary-button labels, focus rings and meaningful control borders. Terminal programmes can choose arbitrary foreground/background combinations; those combinations are outside the guarantee. Plugin graphs and third-party decorations need their own contextual checks.

## Transparency and motion

Opaque content surfaces preserve the measurements. When integrating the exported tokens into an application, keep text on opaque surfaces. Decorative effects must stay behind an opaque text backplate or be composited and retested. Do not reduce label opacity to create hierarchy; use `text.secondary` or `text.muted`.

Clipping/error feedback must include labels or symbols; colour alone is insufficient. Keyboard operation, names, focus order, zoom, screen-reader semantics and application-specific rendering remain separate accessibility obligations. A palette cannot certify legal or whole-product WCAG conformance.

## Native format references

- [VS Code theme extension guide](https://code.visualstudio.com/api/extension-guides/color-theme) and [workbench colour keys](https://code.visualstudio.com/api/references/theme-color).
- [Windows Terminal colour schemes](https://learn.microsoft.com/en-us/windows/terminal/customize-settings/color-schemes).
- [Kitty configuration](https://sw.kovidgoyal.net/kitty/conf/).
- [Alacritty configuration](https://alacritty.org/config-alacritty.html).
- [WezTerm appearance](https://wezterm.org/config/appearance.html).
- [Neovim API](https://neovim.io/doc/user/api.html).
