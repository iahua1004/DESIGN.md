# DESIGN.md authoring template

Use this when **generating a new DESIGN.md** (workflow B: extract from a website, a
screenshot, or a verbal description). It matches `format A` — the tokenised layout used by
64 of the 74 files in `VoltAgent/awesome-design-md` — so `lint`, `--css-vars` and
`--tokens-only` all work on the result.

Two hard conventions:

1. **Every colour role gets an explicit hex AND a one-line job description.**
2. **Body text references tokens, not raw hex**: write `` `{colors.canvas}` ``, not `#010102`.
   The script resolves these; hand-written hex in prose cannot be checked.

---

```markdown
---
version: alpha
name: <Site>-design-analysis
description: "<= 3 sentences: overall mood, canvas colour + accent hex, the one thing that
  makes this system recognisable.>"

colors:
  canvas: "#ffffff"          # page background
  surface-1: "#f6f9fc"       # cards / panels, one step above canvas
  surface-2: "#eef2f7"       # nested surfaces
  ink: "#0d253d"             # primary text
  ink-muted: "#64748d"       # secondary text
  ink-subtle: "#94a3b8"      # captions, metadata
  hairline: "#e3e8ee"        # 1px borders, dividers
  primary: "#533afd"         # brand accent — state its allowed usages in the Do's
  primary-hover: "#4434d4"
  primary-pressed: "#2e2b8c"
  on-primary: "#ffffff"      # text on top of primary
  semantic-success: "#27a644"
  semantic-warning: "#f5a623"
  semantic-danger: "#ea2261"
  overlay: "#000000"         # modal scrim

typography:
  display-xl:
    fontFamily: "<family>, <fallback stack>"
    fontSize: 56px
    fontWeight: 300
    lineHeight: 1.03
    letterSpacing: -1.4px
  display-lg: { fontFamily: "...", fontSize: 40px, fontWeight: 300, lineHeight: 1.10, letterSpacing: -1.0px }
  headline:   { fontFamily: "...", fontSize: 28px, fontWeight: 500, lineHeight: 1.20, letterSpacing: -0.4px }
  card-title: { fontFamily: "...", fontSize: 20px, fontWeight: 500, lineHeight: 1.30, letterSpacing: -0.2px }
  body:       { fontFamily: "...", fontSize: 16px, fontWeight: 400, lineHeight: 1.60, letterSpacing: 0 }
  body-sm:    { fontFamily: "...", fontSize: 14px, fontWeight: 400, lineHeight: 1.50, letterSpacing: 0 }
  caption:    { fontFamily: "...", fontSize: 12px, fontWeight: 400, lineHeight: 1.40, letterSpacing: 0.2px }
  button:     { fontFamily: "...", fontSize: 14px, fontWeight: 500, lineHeight: 1.0, letterSpacing: 0 }
  mono:       { fontFamily: "ui-monospace, Menlo, monospace", fontSize: 13px, fontWeight: 400, lineHeight: 1.5, letterSpacing: 0 }

rounded:
  xs: 4px
  sm: 6px
  md: 8px
  lg: 12px
  xl: 16px
  pill: 9999px

spacing:
  xxs: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  xxl: 48px
  section: 96px

components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button}"
    rounded: 8px
    padding: 8px 14px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
    typography: "{typography.button}"
    rounded: 8px
  button-secondary:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    typography: "{typography.button}"
    rounded: 8px
  input:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
    borderColor: "{colors.hairline}"
    rounded: 6px
    padding: 8px 12px
  card:
    backgroundColor: "{colors.surface-1}"
    textColor: "{colors.ink}"
    rounded: "{rounded.lg}"
    padding: 24px
  nav-bar:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
---

## Overview
Mood, density, and design philosophy in prose. Name the canvas colour and the single
accent, then a `**Key Characteristics:**` bullet list of 5-9 concrete, checkable traits
(exact radii, exact tracking values, what is deliberately absent).

## Colors
Group by role — Brand & Accent / Surface / Text / Semantic. For each: name, hex, and the
one thing it is allowed to do.

## Typography
`### Font Families`, then a `### Hierarchy` markdown table with columns
`| Role | Size | Weight | Line Height | Letter Spacing | Notes |`, then `### Principles`.

## Layout
`### Spacing System` (the scale in use), `### Grid & Container` (column count, gutter,
max-width), `### Whitespace Philosophy`.

## Shapes
Radius usage per component class, border weights, whether pills are allowed anywhere.

## Components
Buttons (default / hover / pressed / disabled), cards (default / featured), inputs
(default / focus / error), navigation. Give background, text, radius, padding, typography
for each state.

## Elevation & Depth
The shadow ladder with literal `box-shadow` values, and which surface level earns which
shadow. Say explicitly if the system uses hairlines instead of shadows.

## Do's and Don'ts
`### Do` and `### Don't` bullet lists. This is the section agents actually obey — be
specific and negative where it matters ("Don't pill-round CTAs", "Don't introduce a
second chromatic accent").

## Responsive Behavior
Breakpoints, `### Touch Targets` (minimum sizes), `### Collapsing` (what stacks, what
hides, what becomes a drawer).

## Iteration Guide
Quick-reference colour table plus 2-3 ready-to-use prompts an agent can paste.

## Known Gaps
What could not be observed. Say "not observed" rather than guessing.
```

---

## Notes on filling it in

- If the source is a **screenshot**, you can usually fill `colors`, `typography`
  (approximate sizes), `rounded` and `components` — mark estimates in Known Gaps.
- If a role genuinely cannot be determined, **omit the key** and say so in Known Gaps.
  An absent token is honest; a guessed hex poisons every later generation.
- `letterSpacing: 0` is a valid and meaningful answer (Tesla uses `normal` everywhere).
- After writing, always run `lint <path>`; it checks frontmatter keys, hex validity,
  `{token}` resolvability and section coverage.
