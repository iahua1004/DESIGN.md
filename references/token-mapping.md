# Token → CSS mapping rules

Rules for turning `--css-vars` output into actual styles. Follow these mechanically;
do not hand-copy hex values.

## Variable naming

| token path | CSS variable |
|---|---|
| `colors.<name>` | `--md-color-<name>` |
| `typography.<role>.fontFamily` | `--md-font-<role>-family` |
| `typography.<role>.fontSize` | `--md-font-<role>-size` |
| `typography.<role>.fontWeight` | `--md-font-<role>-weight` |
| `typography.<role>.lineHeight` | `--md-font-<role>-height` |
| `typography.<role>.letterSpacing` | `--md-font-<role>-spacing` |
| `fontFamilies.<name>` (legacy only) | `--md-font-family-<name>` |
| `rounded.<step>` | `--md-radius-<step>` |
| `spacing.<step>` | `--md-space-<step>` |
| `components.<name>.backgroundColor` | `--md-<name>-bg` |
| `components.<name>.textColor` | `--md-<name>-fg` |
| `components.<name>.rounded` | `--md-<name>-radius` |
| `components.<name>.padding` | `--md-<name>-padding` |
| `components.<name>.typography` | expanded to `--md-<name>-family/-size/-weight/-height/-spacing` |

## Unit normalisation

- `lineHeight: 1.20` → `line-height: 1.2` (unitless multiplier, do NOT append px)
- `fontWeight: 600` → `font-weight: 600`
- `fontSize: 80px` → keep px
- `letterSpacing: -3.0px` → keep px; `0` → `0`; `normal` → `normal`
- `padding: 8px 14px` → use as-is
- Legacy tables sometimes write `40px (2.50rem)` — the script keeps the first value (`40px`).
  For line-height it keeps the unitless ratio inside the parentheses (`1.20`).

## Font fallback

Proprietary families are almost never installed locally. Always extend the stack;
never let a missing family fall back to the browser default serif.

| declared family | fallback chain |
|---|---|
| `Linear Display` / `Linear Text` | `"Linear Display", "SF Pro Display", Inter, -apple-system, system-ui, sans-serif` |
| `Sohne` / `sohne-var` (Stripe) | `sohne-var, "SF Pro Text", -apple-system, Inter, system-ui, sans-serif` |
| `Universal Sans Display` (Tesla) | `"Universal Sans Display", "SF Pro Display", Inter, Arial, sans-serif` |
| `Geist` (Vercel) | `Geist, "SF Pro Text", -apple-system, Inter, system-ui, sans-serif` |
| any `Mono` / `SF Mono` / `Monaco` | `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` |
| unknown proprietary | `<declared>, -apple-system, "Segoe UI", Roboto, Inter, system-ui, sans-serif` |

Do not `<link>` a webfont CDN unless the user explicitly accepts external requests; if you
do, add `font-display: swap` and keep the fallback stack so text is never invisible.

## Missing dimensions

If a token you need is absent, derive it from what exists and mark it in a CSS comment:

```css
/* derived: components.input missing in source, built from surface-1 + hairline */
--md-input-bg: var(--md-color-surface-1);
--md-input-border: var(--md-color-hairline);
--md-input-radius: var(--md-radius-md);
```

Never invent a hex that is not in the token set. Never invent a spacing/radius value that
is not on the declared scale (no `13px`, no `7px`).

## Light / dark

Many brands ship **only one** polarity — Linear explicitly forbids a light marketing page.
Check `--section dos`; if only one theme is documented, produce only that theme. Do not
fabricate the other one.

## Consistency checklist (run before delivering)

1. `grep -o '#[0-9a-fA-F]\{6\}' output.html | sort -u` — every hit must exist in
   `fetch <brand> --css-vars`. Any hex not in that list is fabricated → replace with a var.
2. Radius and spacing values must appear in the `--md-radius-*` / `--md-space-*` lists.
3. `contrast <ink> <canvas>` ≥ 4.5:1 and `contrast <on-primary> <primary>` ≥ 4.5:1.
4. Accent colour usage matches the Do's and Don'ts (e.g. Linear: lavender only on brand
   mark, focus ring, primary CTA).
5. Comment the source URL and MIT attribution at the top of the delivered file.
