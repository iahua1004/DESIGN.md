#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
design-md — fetch and apply DESIGN.md design systems from VoltAgent/awesome-design-md.

Zero third-party dependencies (no requests, no PyYAML).
Subcommands: list, search, fetch, contrast, lint, probe-site, sync-brands, mirrors

Exit codes:
  0  success
  1  lint failure / usage error
  2  brand not found
  3  network failure (all sources exhausted)
  4  document format abnormal
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from collections import OrderedDict
from html.parser import HTMLParser

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCES_DIR = os.path.join(SKILL_DIR, "references")
BRANDS_FILE = os.path.join(REFERENCES_DIR, "brands.md")
MIRRORS_FILE = os.path.join(REFERENCES_DIR, "mirrors.json")

OFFICIAL_REPO = "https://github.com/VoltAgent/awesome-design-md"
DEFAULT_MIRRORS = {
    "_comment": "Fetch sources in priority order. {dir} is replaced by the brand directory "
                "name (e.g. linear.app). Fill in your own gitee / github mirror URLs and set "
                "\"enabled\": true to put them ahead of the official source.",
    "sources": [
        {"name": "gitee", "enabled": False,
         "url": "https://gitee.com/OWNER/REPO/raw/main/design-md/{dir}/DESIGN.md"},
        {"name": "github-mirror", "enabled": False,
         "url": "https://raw.githubusercontent.com/OWNER/REPO/main/design-md/{dir}/DESIGN.md"},
        {"name": "official-raw", "enabled": True,
         "url": "https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/{dir}/DESIGN.md"},
        {"name": "jsdelivr", "enabled": True,
         "url": "https://cdn.jsdelivr.net/gh/VoltAgent/awesome-design-md@main/design-md/{dir}/DESIGN.md"},
    ],
}

UA = "design-md-skill/1.0 (+local agent skill)"

CANONICAL_SECTIONS = OrderedDict([
    ("overview",   ["overview", "visual theme & atmosphere", "visual theme and atmosphere",
                    "theme & atmosphere"]),
    ("colors",     ["colors", "color palette & roles", "color palette and roles", "color"]),
    ("typography", ["typography", "typography rules", "type"]),
    ("components", ["components", "component stylings", "component styling"]),
    ("layout",     ["layout", "layout principles"]),
    ("elevation",  ["elevation & depth", "elevation and depth", "depth & elevation",
                    "depth and elevation", "elevation"]),
    ("shapes",     ["shapes", "shape"]),
    ("dos",        ["do's and don'ts", "dos and don'ts", "do's & don'ts", "dos"]),
    ("responsive", ["responsive behavior", "responsive"]),
    ("agent",      ["agent prompt guide", "iteration guide", "known gaps", "prompt guide"]),
])

TYPO_PROPS = {
    "fontfamily": "family", "fontsize": "size", "fontweight": "weight",
    "lineheight": "height", "letterspacing": "spacing", "texttransform": "transform",
    "fontfeature": "feature",
}

COMP_PROPS = {
    "backgroundcolor": "bg", "background": "bg", "backgroundcolour": "bg",
    "textcolor": "fg", "color": "fg", "textcolour": "fg",
    "bordercolor": "border-color", "bordercolour": "border-color",
    "rounded": "radius", "borderradius": "radius", "padding": "padding",
    "shadow": "shadow", "elevation": "shadow", "typography": "typography",
    "border": "border", "width": "width", "height": "height",
}


# --------------------------------------------------------------------------- #
# HTTP                                                                         #
# --------------------------------------------------------------------------- #

def _urllib_get(url, timeout=15):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "*/*",
        "Accept-Encoding": "identity",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def _curl_get(url, timeout=25):
    try:
        out = subprocess.run(
            ["/usr/bin/curl", "-sSL", "--max-time", str(timeout), "-A", UA, url],
            capture_output=True, timeout=timeout + 10,
        )
        if out.returncode == 0:
            return out.stdout.decode("utf-8", "replace")
    except Exception:
        pass
    return None


def http_get(url, tries=2, validate=None):
    """Try urllib, then curl, with retries. Returns text or None."""
    last_err = None
    for attempt in range(tries):
        for getter in (_urllib_get, _curl_get):
            try:
                text = getter(url)
                if text and (validate is None or validate(text)):
                    return text
            except Exception as exc:  # noqa: BLE001
                last_err = exc
        if attempt < tries - 1:
            time.sleep(0.8 * (attempt + 1))
    if last_err:
        sys.stderr.write("  ! %s -> %s\n" % (url, last_err))
    return None


def _looks_like_design_md(text):
    text = text.lstrip()
    if not text:
        return False
    return text.startswith("---") or text.startswith("#")


def load_mirrors():
    if not os.path.exists(MIRRORS_FILE):
        return DEFAULT_MIRRORS
    try:
        with open(MIRRORS_FILE, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict) and data.get("sources"):
            return data
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("! mirrors.json unreadable (%s), falling back to defaults\n" % exc)
    return DEFAULT_MIRRORS


def fetch_doc(brand_dir):
    """Fetch DESIGN.md for a brand directory. Returns (text, source_name) or (None, None)."""
    mirrors = load_mirrors()
    sources = [s for s in mirrors.get("sources", []) if s.get("enabled", True)]
    if not sources:
        sources = DEFAULT_MIRRORS["sources"]
    tried = []
    for src in sources:
        url = src["url"].replace("{dir}", brand_dir)
        tried.append(src["name"])
        text = http_get(url, tries=2, validate=_looks_like_design_md)
        if text:
            if len(tried) > 1:
                sys.stderr.write("  (used fallback source: %s)\n" % src["name"])
            return text, src["name"]
    sys.stderr.write("! all %d sources failed: %s\n" % (len(tried), ", ".join(tried)))
    return None, None


# --------------------------------------------------------------------------- #
# YAML subset parser                                                           #
# --------------------------------------------------------------------------- #

def _unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
        return v[1:-1]
    return v


def parse_yaml_subset(text):
    """Parse the small YAML subset used by DESIGN.md frontmatter.

    Supports: nested dicts by indentation, scalars, quoted scalars, block
    scalars (| and >), inline lists in [a, b] form, list items with '- '.
    Comment stripping is deliberately NOT implemented: descriptions contain
    literal hex values like '#5e6ad2' which would be truncated.
    """
    root = OrderedDict()
    stack = [(-1, root)]
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content = raw.strip()
        if content.startswith("#"):
            continue

        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        # list item under a key
        if content.startswith("- "):
            item = _unquote(content[2:])
            if isinstance(parent, list):
                parent.append(item)
            continue

        if ":" not in content:
            continue

        key, _, rest = content.partition(":")
        key = key.strip()
        rest = rest.strip()

        if rest in ("|", ">", "|-", ">-", "|+"):
            block = []
            base = None
            while i < len(lines):
                nl = lines[i]
                if not nl.strip():
                    block.append("")
                    i += 1
                    continue
                nind = len(nl) - len(nl.lstrip(" "))
                if base is None:
                    base = nind
                if nind < base:
                    break
                block.append(nl.strip())
                i += 1
            parent[key] = "\n".join(block).strip()
            continue

        if rest == "":
            child = OrderedDict()
            parent[key] = child
            stack.append((indent, child))
            continue

        if rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1].strip()
            if inner:
                parent[key] = [_unquote(x) for x in inner.split(",")]
            else:
                parent[key] = []
            continue

        parent[key] = _unquote(rest)
    return root


# --------------------------------------------------------------------------- #
# Document splitting & token extraction                                        #
# --------------------------------------------------------------------------- #

def split_doc(text):
    """Return (fmt, frontmatter_text, body). fmt is 'A' (frontmatter) or 'B' (legacy)."""
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                fm = "\n".join(lines[1:i])
                body = "\n".join(lines[i + 1:])
                return "A", fm, body
    return "B", "", text


HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
NAMED_COLOR_RE = re.compile(
    r"\*\*([^*]{2,40}?)\*\*\s*[（(]\s*`?(#[0-9a-fA-F]{6})`?\s*[)）]")


def extract_tokens(fmt, fm_text, body):
    tokens = OrderedDict()
    if fmt == "A":
        fm = parse_yaml_subset(fm_text)
        meta = OrderedDict()
        for k in ("version", "name", "description"):
            if k in fm:
                meta[k] = fm[k]
        tokens["meta"] = meta
        tokens["_source"] = "frontmatter"
        for key in ("colors", "typography", "rounded", "spacing", "components", "shadows"):
            if key in fm and isinstance(fm[key], dict) and fm[key]:
                tokens[key] = fm[key]
        return tokens

    # ---- format B: heuristic extraction ----
    tokens["_source"] = "heuristic"
    colors = OrderedDict()
    for m in NAMED_COLOR_RE.finditer(body):
        name = m.group(1).strip()
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if slug and slug not in colors:
            colors[slug] = m.group(2)
    if not colors:
        seen = []
        for m in HEX_RE.finditer(body):
            h = m.group(0).lower()
            if h not in seen:
                seen.append(h)
        for idx, h in enumerate(seen[:14]):
            colors["color-%02d" % (idx + 1)] = h
    tokens["colors"] = colors

    typo = _extract_typography_table(body)
    if typo:
        tokens["typography"] = typo

    fams = _extract_font_families(body)
    if fams:
        tokens["fontFamilies"] = fams

    radii = OrderedDict()
    for idx, val in enumerate(sorted(set(re.findall(
            r"border-radius:\s*([0-9]+px|50%|[0-9]+%)", body)))[:8]):
        radii["r%d" % (idx + 1)] = val
    if radii:
        tokens["rounded"] = radii
    return tokens


FONT_BULLET_RE = re.compile(r"^\s*[-*]\s*\*\*([^*]{1,30}?)\*\*\s*[:：]\s*(.+)$", re.M)


def _extract_font_families(body):
    """Format B stores stacks as bullets like: - **Display**: `X`, -apple-system, ...

    Only the heading region that actually talks about fonts is scanned,
    otherwise every bold bullet in the document is mistaken for a font.
    """
    region = body
    head = re.search(r"^#{2,4}\s+.*\b(font|typeface)\b.*$", body, re.M | re.I)
    if head:
        start = head.end()
        nxt = re.search(r"^#{2,4}\s+", body[start:], re.M)
        region = body[start:start + nxt.start()] if nxt else body[start:]
    fams = OrderedDict()
    for m in FONT_BULLET_RE.finditer(region[:6000]):
        name = m.group(1).strip()
        val = m.group(2).strip()
        val = re.split(r"\s+[—–-]\s+|\s+used for\s+", val)[0]
        val = val.strip().rstrip(".,;").replace("`", "")
        if not re.search(r"[a-zA-Z]{3}", val):
            continue
        if len(val) > 120:
            val = val[:120]
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if slug and slug not in fams:
            fams[slug] = val
    return fams or None


def _extract_typography_table(body):
    """Parse markdown tables that look like: | Role | Font | Size | Weight | ..."""
    rows = []
    header = None
    for line in body.split("\n"):
        s = line.strip()
        if not s.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells:
            continue
        if all(re.fullmatch(r":?-{2,}:?", c) or c == "" for c in cells):
            continue
        if header is None:
            header = cells
        else:
            rows.append(cells)
    if not header or not rows:
        return None
    low = [h.lower() for h in header]

    def col(*cands):
        for idx, h in enumerate(low):
            for c in cands:
                if c in h:
                    return idx
        return None

    c_role = col("role", "level", "name", "style")
    c_font = col("font", "family", "typeface")
    c_size = col("size", "font-size")
    c_weight = col("weight")
    c_lh = col("line height", "line-height", "leading")
    c_ls = col("letter spacing", "letter-spacing", "tracking")
    if c_size is None and c_font is None:
        return None

    typo = OrderedDict()
    for r in rows:
        def get(c):
            return r[c] if (c is not None and c < len(r)) else None
        role_raw = get(c_role) or ("type-%d" % (len(typo) + 1))
        slug = re.sub(r"[^a-z0-9]+", "-", role_raw.lower()).strip("-") or \
            "type-%d" % (len(typo) + 1)
        entry = OrderedDict()
        if get(c_font):
            entry["fontFamily"] = get(c_font).strip("`* ")
        if get(c_size):
            entry["fontSize"] = get(c_size).strip("`* ")
        if get(c_weight):
            entry["fontWeight"] = get(c_weight).strip("`* ")
        if get(c_lh):
            entry["lineHeight"] = get(c_lh).strip("`* ")
        if get(c_ls):
            entry["letterSpacing"] = get(c_ls).strip("`* ")
        if entry and slug not in typo:
            typo[slug] = entry
    return typo or None


def _lookup_path(path, root):
    cur = root
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _resolvable(path, tokens):
    """True if {path} resolves directly or under one of the token groups."""
    if _lookup_path(path, tokens) is not None:
        return True
    for group in ("colors", "typography", "rounded", "spacing", "components", "fontFamilies"):
        g = tokens.get(group)
        if isinstance(g, dict) and _lookup_path(path, g) is not None:
            return True
    return False


def resolve_expr(value, tokens, depth=0):
    """Resolve {a.b.c} references against the token tree."""
    if depth > 6:
        return value
    if not isinstance(value, str):
        return value

    def lookup(path):
        return _lookup_path(path, tokens)

    def repl(m):
        got = lookup(m.group(1))
        if got is None:
            return m.group(0)
        got = resolve_expr(got, tokens, depth + 1)
        if isinstance(got, dict):
            return m.group(0)
        return str(got)

    out = re.sub(r"\{([a-zA-Z][\w.\-]*)\}", repl, value)
    if out == value:
        return value
    return out


def resolve_all(node, tokens):
    if isinstance(node, dict):
        return OrderedDict((k, resolve_all(v, tokens)) for k, v in node.items())
    if isinstance(node, list):
        return [resolve_all(v, tokens) for v in node]
    return resolve_expr(node, tokens)


# --------------------------------------------------------------------------- #
# CSS rendering                                                                #
# --------------------------------------------------------------------------- #

def _norm_length(v):
    if isinstance(v, (int, float)):
        return str(v)
    return str(v).strip()


def _clean_typo_value(short, v):
    """Legacy tables write '40px (2.50rem)' or '48px (1.20)'. Keep one usable value."""
    v = str(v).strip()
    m = re.match(r"^(-?[0-9.]+(?:px|rem|em|%)?)\s*\(([^)]+)\)\s*$", v)
    if m:
        first, paren = m.group(1), m.group(2)
        if short == "height":
            pm = re.search(r"([0-9.]+)", paren)
            if pm and not re.search(r"(px|rem|em)", paren):
                return pm.group(1)
        return first
    m = re.match(r"^(-?[0-9.]+(?:px|rem|em|%)?)", v)
    if m and (short in ("size", "weight", "height", "spacing")):
        return m.group(1)
    return v


def render_css_vars(tokens):
    resolved = resolve_all(
        OrderedDict((k, v) for k, v in tokens.items() if not k.startswith("_")), tokens)
    out = [":root {"]
    out.append("  /* source: %s */" % tokens.get("_source", "unknown"))

    for name, val in (resolved.get("colors") or {}).items():
        if isinstance(val, str):
            out.append("  --md-color-%s: %s;" % (name, val))

    for name, val in (resolved.get("fontFamilies") or {}).items():
        if isinstance(val, str):
            out.append("  --md-font-family-%s: %s;" % (name, val))

    for role, props in (resolved.get("typography") or {}).items():
        if not isinstance(props, dict):
            continue
        for prop, val in props.items():
            short = TYPO_PROPS.get(prop.lower(), prop.lower())
            v = _clean_typo_value(short, val)
            if short in ("size", "height", "weight") and not re.search(r"[0-9]", str(v)):
                continue  # placeholders like "—" or "est." are not usable values
            out.append("  --md-font-%s-%s: %s;" % (role, short, v))

    for name, val in (resolved.get("rounded") or {}).items():
        if not isinstance(val, dict):
            out.append("  --md-radius-%s: %s;" % (name, _norm_length(val)))

    for name, val in (resolved.get("spacing") or {}).items():
        if not isinstance(val, dict):
            out.append("  --md-space-%s: %s;" % (name, _norm_length(val)))

    for cname, props in (resolved.get("components") or {}).items():
        if not isinstance(props, dict):
            continue
        for prop, val in props.items():
            short = COMP_PROPS.get(prop.lower(), prop.lower())
            if short == "typography":
                target = val
                if isinstance(target, str):
                    m = re.fullmatch(r"\{typography\.([\w\-]+)\}", target.strip())
                    if m:
                        target = (resolved.get("typography") or {}).get(m.group(1))
                if isinstance(target, dict):
                    for tp, tv in target.items():
                        tshort = TYPO_PROPS.get(tp.lower(), tp.lower())
                        out.append("  --md-%s-%s: %s;" % (
                            cname, tshort, _clean_typo_value(tshort, tv)))
                continue
            if not isinstance(val, dict):
                out.append("  --md-%s-%s: %s;" % (cname, short, _norm_length(val)))
    out.append("}")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Contrast                                                                     #
# --------------------------------------------------------------------------- #

def _srgb_to_lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def parse_hex(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) == 8:
        h = h[:6]
    if len(h) != 6:
        raise ValueError("not a hex color: %s" % h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def contrast_ratio(fg, bg):
    r1, g1, b1 = parse_hex(fg)
    r2, g2, b2 = parse_hex(bg)
    l1 = 0.2126 * _srgb_to_lin(r1) + 0.7152 * _srgb_to_lin(g1) + 0.0722 * _srgb_to_lin(b1)
    l2 = 0.2126 * _srgb_to_lin(r2) + 0.7152 * _srgb_to_lin(g2) + 0.0722 * _srgb_to_lin(b2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def grade(ratio):
    if ratio >= 7:
        return "AAA"
    if ratio >= 4.5:
        return "AA"
    if ratio >= 3:
        return "AA-large"
    return "FAIL"


# --------------------------------------------------------------------------- #
# Brand index                                                                  #
# --------------------------------------------------------------------------- #

def load_index():
    if not os.path.exists(BRANDS_FILE):
        raise SystemExit("! brand index missing: %s (run: sync-brands --write)" % BRANDS_FILE)
    rows = []
    with open(BRANDS_FILE, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 5:
                continue
            if cells[0] in ("dir", "---") or set(cells[0]) <= set("-: "):
                continue
            rows.append({
                "dir": cells[0],
                "display": cells[1],
                "category": cells[2],
                "style": cells[3],
                "aliases": [a.strip() for a in cells[4].split(",") if a.strip()],
            })
    if not rows:
        raise SystemExit("! brand index empty or malformed: %s" % BRANDS_FILE)
    return rows


def _norm(s):
    s = s.lower().strip()
    s = re.sub(r"[\s_\u3000]+", "", s)
    s = re.sub(r"\.app$|\.ai$|\.com$", "", s)
    s = re.sub(r"-\d{4}$", "", s)
    s = re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", s)
    return s


def resolve_brand(query, index=None):
    """Six-layer fuzzy match. Returns (row, method, score) or (None, None, 0)."""
    import difflib
    index = index if index is not None else load_index()
    q = query.strip()
    qn = _norm(q)

    for row in index:
        if q == row["dir"]:
            return row, "exact", 1.0
    for row in index:
        if q.lower() == row["display"].lower():
            return row, "display", 0.98
    for row in index:
        if qn == _norm(row["dir"]):
            return row, "normalized", 0.96
    for row in index:
        if qn == _norm(row["display"]):
            return row, "normalized-display", 0.94

    for row in index:
        for alias in row["aliases"]:
            if _norm(alias) == qn:
                return row, "alias", 0.92

    scored = []
    for row in index:
        best = 0.0
        cands = [_norm(row["dir"]), _norm(row["display"])] + [_norm(a) for a in row["aliases"]]
        for c in cands:
            if not c:
                continue
            if c.startswith(qn) or qn.startswith(c):
                best = max(best, 0.80)
            r = difflib.SequenceMatcher(None, qn, c).ratio()
            if r > 0.72:
                best = max(best, r * 0.88)
            if c and c in qn:
                best = max(best, 0.70)
            if qn and qn in c:
                best = max(best, 0.68)
        if best > 0:
            scored.append((best, row))
    scored.sort(key=lambda x: -x[0])
    if scored:
        return scored[0][1], "fuzzy", scored[0][0]
    return None, None, 0.0


def candidates(query, index=None, top=5):
    import difflib
    index = index if index is not None else load_index()
    qn = _norm(query)
    scored = []
    for row in index:
        cands = [_norm(row["dir"]), _norm(row["display"])] + [_norm(a) for a in row["aliases"]]
        best = max(difflib.SequenceMatcher(None, qn, c).ratio() for c in cands if c) or 0.0
        scored.append((best, row))
    scored.sort(key=lambda x: -x[0])
    return [(s, r) for s, r in scored[:top] if s > 0.3]


# --------------------------------------------------------------------------- #
# Sections                                                                     #
# --------------------------------------------------------------------------- #

def _canon(title):
    t = re.sub(r"^\d+\.\s*", "", title.strip()).strip().lower()
    t = t.replace("**", "")
    for key, variants in CANONICAL_SECTIONS.items():
        if t == key or t in variants:
            return key
    return t


def list_sections(body):
    out = []
    for m in re.finditer(r"^##\s+(.+)$", body, re.M):
        out.append((_canon(m.group(1)), m.group(1).strip()))
    return out


def pick_sections(body, wanted):
    wanted = set(wanted)
    parts = re.split(r"^##\s+.+$", body, flags=re.M)
    heads = [(m.group(1).strip(), m.start()) for m in re.finditer(r"^##\s+(.+)$", body, re.M)]
    out = []
    for idx, (title, start) in enumerate(heads):
        key = _canon(title)
        if key in wanted:
            end = heads[idx + 1][1] if idx + 1 < len(heads) else len(body)
            out.append(body[start:end].rstrip())
    if not out:
        return None
    return "\n\n".join(out)


# --------------------------------------------------------------------------- #
# Commands                                                                     #
# --------------------------------------------------------------------------- #

def cmd_list(args):
    rows = load_index()
    if args.category:
        rows = [r for r in rows if r["category"].lower() == args.category.lower()]
        if not rows:
            sys.stderr.write("! no brand in category '%s'\n" % args.category)
            return 1
    if args.format == "names":
        for r in rows:
            print(r["dir"])
        return 0
    if args.format == "json":
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    print("| dir | display | category | style |")
    print("|-----|---------|----------|-------|")
    for r in rows:
        print("| %s | %s | %s | %s |" % (r["dir"], r["display"], r["category"], r["style"]))
    print("\n(%d brands)" % len(rows))
    return 0


CATEGORY_KEYWORDS = {
    "ai": ["人工智能", "大模型", "llm", "ai", "智能", "对话", "语音", "生成", "推理", "agent"],
    "devtools": ["编辑器", "开发工具", "终端", "命令行", "部署", "前端", "ide", "编程"],
    "backend": ["数据库", "后端", "数据", "监控", "分析", "基础设施", "存储", "服务端", "埋点"],
    "saas": ["协作", "效率", "工具", "文档", "日程", "客服", "邮件", "自动化", "管理", "办公"],
    "design": ["设计", "创意", "白板", "原型", "建站", "视觉", "画板"],
    "fintech": ["金融", "支付", "财务", "银行", "交易", "加密", "钱包", "汇款", "收款", "结算"],
    "commerce": ["电商", "零售", "商城", "购物", "商品", "预订", "民宿", "外卖", "咖啡"],
    "media": ["媒体", "内容", "音乐", "影音", "游戏", "社交", "杂志", "硬件", "消费电子"],
    "auto": ["汽车", "豪车", "跑车", "车企", "座驾", "机车"],
    "retro": ["复古", "怀旧", "年代", "像素", "y2k", "千禧", "老网页", "怀旧风"],
}


def cmd_search(args):
    import difflib
    rows = load_index()
    q = args.query
    ql = q.lower()
    qplain = re.sub(r"[\s\u3000]+", "", ql)
    qn = _norm(q)
    # Chinese queries have no spaces, so individual words must be found by
    # substring rather than by splitting the query.
    toks = set(re.findall(r"[\u4e00-\u9fff]+|[a-z0-9]+", ql))
    scored = []
    for r in rows:
        hay = " ".join([r["dir"], r["display"], r["category"], r["style"]] + r["aliases"]).lower()
        hayn = _norm(hay)
        score = 0.0
        cat = r["category"].lower()
        cat_kw = CATEGORY_KEYWORDS.get(cat, [])

        if cat and cat in qplain:
            score += 0.45
        for kw in cat_kw:
            if kw in qplain:
                score += 0.45

        names = [r["dir"], r["display"]] + r["aliases"]
        for n in names:
            nn = _norm(n)
            if not nn:
                continue
            if nn in qplain or nn in ql:
                score += 0.55

        for t in toks:
            if len(t) < 2:
                continue
            if t in hayn:
                score += 0.25
            if t in cat_kw:
                score += 0.45

        best = 0.0
        for n in names:
            nn = _norm(n)
            if nn:
                best = max(best, difflib.SequenceMatcher(None, qn, nn).ratio())
        if best > 0.6:
            score += best * 0.5

        if score > 0:
            scored.append((score, r))
    scored.sort(key=lambda x: (-x[0], x[1]["dir"]))
    top = scored[:args.top]
    if not top:
        sys.stderr.write("! nothing matched '%s'; try: list, or a brand name\n" % q)
        return 2
    if args.json:
        print(json.dumps([{"dir": r["dir"], "display": r["display"],
                           "category": r["category"], "style": r["style"],
                           "score": round(s, 3)} for s, r in top],
                         ensure_ascii=False, indent=2))
        return 0
    for s, r in top:
        print("%-16s %-5.2f  %-9s %s" % (r["dir"], s, r["category"], r["style"]))
    return 0


def cmd_fetch(args):
    index = load_index()
    row, method, score = resolve_brand(args.brand, index)
    if not row:
        sys.stderr.write("! brand not found: '%s'\n\nDid you mean:\n" % args.brand)
        for s, r in candidates(args.brand, index, 5):
            sys.stderr.write("  %-16s %s\n" % (r["dir"], r["style"]))
        sys.stderr.write("\nRun `list` to see all brands.\n")
        return 2

    if method == "fuzzy" and score < 0.80:
        sys.stderr.write("! ambiguous brand '%s' (best match %.2f, not confident).\n"
                         "Candidates:\n" % (args.brand, score))
        for s, r in candidates(args.brand, index, 5):
            sys.stderr.write("  %-16s %s\n" % (r["dir"], r["style"]))
        sys.stderr.write("\nRe-run with an exact dir name, e.g.: fetch %s\n" % row["dir"])
        return 2

    text, source = fetch_doc(row["dir"])
    if not text:
        sys.stderr.write("! network failure fetching %s (exit 3)\n" % row["dir"])
        return 3
    fmt, fm_text, body = split_doc(text)
    if fmt == "B" and not body.strip().startswith("#"):
        sys.stderr.write("! unexpected document shape for %s\n" % row["dir"])
        return 4

    if args.out:
        path = os.path.abspath(args.out)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print("wrote %s (%d bytes, format %s, source %s)" % (path, len(text), fmt, source))
        return 0

    tokens = extract_tokens(fmt, fm_text, body)

    if args.raw:
        print(text[:args.max_chars] if len(text) > args.max_chars else text)
        return 0

    if args.section:
        keys = [k.strip() for k in args.section.split(",")]
        picked = pick_sections(body, keys)
        if picked is None:
            print("! no section matched %s in %s. Available sections:" % (keys, row["dir"]))
            for key, title in list_sections(body):
                print("  %-12s %s" % (key, title))
            return 1
        if len(picked) > args.max_chars:
            picked = picked[:args.max_chars] + "\n\n...TRUNCATED"
        print(picked)
        return 0

    if args.css_vars:
        print(render_css_vars(tokens))
        return 0

    if args.json:
        payload = OrderedDict()
        payload["dir"] = row["dir"]
        payload["display"] = row["display"]
        payload["format"] = fmt
        payload["source"] = source
        payload["bytes"] = len(text)
        payload["sections"] = [k for k, _ in list_sections(body)]
        resolved = resolve_all(
            OrderedDict((k, v) for k, v in tokens.items() if not k.startswith("_")), tokens)
        payload["tokens"] = resolved
        payload["token_source"] = tokens.get("_source")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if args.tokens_only:
        resolved = resolve_all(
            OrderedDict((k, v) for k, v in tokens.items() if not k.startswith("_")), tokens)
        print("# %s  (format %s, token source: %s, via %s, matched by %s %.2f)"
              % (row["display"], fmt, tokens.get("_source"), source, method, score))
        print()
        print(json.dumps(resolved, ensure_ascii=False, indent=2)[:args.max_chars])
        return 0

    # default: metadata only
    print("brand      : %s (%s)" % (row["display"], row["dir"]))
    print("matched by : %s (%.2f)" % (method, score))
    print("style      : %s" % row["style"])
    print("fetched via: %s" % source)
    print("format     : %s" % ("A (YAML frontmatter)" if fmt == "A" else "B (legacy 9-section)"))
    print("size       : %d bytes (~%d tokens)" % (len(text), len(text) // 4))
    print("token src  : %s" % tokens.get("_source"))
    print("sections   :")
    for key, title in list_sections(body):
        print("   %-12s %s" % (key, title))
    print("\nNext: --css-vars | --tokens-only | --section overview,dos")
    return 0


def cmd_contrast(args):
    try:
        ratio = contrast_ratio(args.fg, args.bg)
    except ValueError as exc:
        sys.stderr.write("! %s\n" % exc)
        return 1
    print("%s on %s -> %.2f:1  %s" % (args.fg, args.bg, ratio, grade(ratio)))
    return 0 if ratio >= 4.5 else 1


def cmd_lint(args):
    path = os.path.abspath(args.path)
    if not os.path.exists(path):
        sys.stderr.write("! file not found: %s\n" % path)
        return 1
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    fmt, fm_text, body = split_doc(text)
    problems = []

    if fmt != "A":
        problems.append("missing YAML frontmatter (expected format A; got legacy format B)")
    else:
        fm = parse_yaml_subset(fm_text)
        for key in ("version", "name", "description", "colors", "typography"):
            if key not in fm:
                problems.append("frontmatter missing key: %s" % key)
        for key in ("colors", "typography"):
            if key in fm and not isinstance(fm[key], dict):
                problems.append("frontmatter key '%s' is not a mapping" % key)
        if isinstance(fm.get("colors"), dict):
            for cname, cval in fm["colors"].items():
                if isinstance(cval, str) and not re.fullmatch(
                        r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})", cval.strip()):
                    problems.append("color '%s' is not a plain hex: %r" % (cname, cval))

    tokens = extract_tokens(fmt, fm_text, body)
    unresolved = set()
    for m in re.finditer(r"\{([a-zA-Z][\w.\-]*)\}", text):
        if not _resolvable(m.group(1), tokens):
            unresolved.add(m.group(0))
    if unresolved:
        problems.append("unresolved token references: %s" % ", ".join(sorted(unresolved)[:12]))

    present = set(k for k, _ in list_sections(body))
    expected = ["overview", "colors", "typography", "components", "layout",
                "elevation", "dos", "responsive", "agent"]
    missing = [e for e in expected if e not in present]
    if missing:
        problems.append("missing/renamed sections: %s" % ", ".join(missing))

    print("lint %s  (format %s)" % (path, fmt))
    print("sections found: %s" % (", ".join(sorted(present)) or "none"))
    if not problems:
        print("OK — no problems found")
        return 0
    print("\n%d problem(s):" % len(problems))
    for p in problems:
        print("  - %s" % p)
    return 1


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.css = []
        self.inline = []
        self.title = ""

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "link":
            rel = (d.get("rel") or "").lower()
            if "stylesheet" in rel and d.get("href"):
                self.css.append(d["href"])
        if tag == "style":
            self.inline.append(1)


def cmd_probe_site(args):
    url = args.url
    if not url.startswith("http"):
        url = "https://" + url
    html = http_get(url, tries=2)
    if not html:
        sys.stderr.write("! network failure fetching %s (exit 3)\n" % url)
        return 3
    parser = _LinkParser()
    try:
        parser.feed(html)
    except Exception:
        pass

    base = url
    css_urls = []
    for href in parser.css[:args.max_css]:
        if href.startswith("//"):
            css_urls.append("https:" + href)
        elif href.startswith("http"):
            css_urls.append(href)
        else:
            css_urls.append(urllib.parse.urljoin(base, href))

    css_text = ""
    for cu in css_urls:
        got = http_get(cu, tries=1)
        if got and len(got) < 300000:
            css_text += "\n" + got

    inline_styles = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", html, re.S | re.I))
    blob = css_text + "\n" + inline_styles

    report = OrderedDict()
    report["url"] = url
    report["css_files"] = len(css_urls)
    report["css_bytes"] = len(blob)

    custom = OrderedDict()
    for m in re.finditer(r"(--[\w-]+)\s*:\s*([^;{}]+);", blob):
        k, v = m.group(1).strip(), m.group(2).strip()
        if k not in custom:
            custom[k] = v
    report["css_custom_properties"] = dict(list(custom.items())[:40])

    freq = OrderedDict()
    for m in HEX_RE.finditer(blob):
        h = m.group(0).lower()
        freq[h] = freq.get(h, 0) + 1
    report["colors_top"] = dict(sorted(freq.items(), key=lambda x: -x[1])[:30])

    fonts = OrderedDict()
    for m in re.finditer(r"font-family\s*:\s*([^;{}]+)", blob):
        v = m.group(1).strip()
        fonts[v] = fonts.get(v, 0) + 1
    report["font_stacks_top"] = dict(sorted(fonts.items(), key=lambda x: -x[1])[:8])

    radii = OrderedDict()
    for m in re.finditer(r"border-radius\s*:\s*([^;{}]+)", blob):
        v = m.group(1).strip()
        radii[v] = radii.get(v, 0) + 1
    report["border_radius_top"] = dict(sorted(radii.items(), key=lambda x: -x[1])[:10])

    shadows = OrderedDict()
    for m in re.finditer(r"box-shadow\s*:\s*([^;{}]+)", blob):
        v = m.group(1).strip()
        shadows[v] = shadows.get(v, 0) + 1
    report["box_shadow_top"] = dict(sorted(shadows.items(), key=lambda x: -x[1])[:8])

    widths = OrderedDict()
    for m in re.finditer(r"max-width\s*:\s*([^;{}]+)", blob):
        v = m.group(1).strip()
        widths[v] = widths.get(v, 0) + 1
    report["max_width_top"] = dict(sorted(widths.items(), key=lambda x: -x[1])[:8])

    report["suspected_csr"] = len(blob) < 2000 and len(custom) == 0

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("url            : %s" % report["url"])
        print("css files      : %d (%d bytes)" % (report["css_files"], report["css_bytes"]))
        print("suspected CSR  : %s" % report["suspected_csr"])
        for key in ("css_custom_properties", "colors_top", "font_stacks_top",
                    "border_radius_top", "box_shadow_top", "max_width_top"):
            print("\n== %s ==" % key)
            items = list(report[key].items())
            if not items:
                print("  (none)")
            for k, v in items[: (12 if key == "css_custom_properties" else 10)]:
                print("  %-28s %s" % (k, v))
        if report["suspected_csr"]:
            print("\n! little CSS found — likely a client-rendered (CSR) site. "
                  "Use the WebFetch tool or ask the user for a screenshot instead.")

    out = json.dumps(report, ensure_ascii=False)
    if len(out) > args.max_chars and not args.json:
        pass
    return 0


def cmd_sync_brands(args):
    api = "https://api.github.com/repos/VoltAgent/awesome-design-md/git/trees/main?recursive=1"
    raw = http_get(api, tries=2)
    if not raw:
        sys.stderr.write("! network failure listing upstream repo (exit 3)\n")
        return 3
    try:
        data = json.loads(raw)
    except Exception:
        sys.stderr.write("! could not parse GitHub tree response\n")
        return 3
    dirs = set()
    for node in data.get("tree", []):
        p = node.get("path", "")
        if p.startswith("design-md/") and p.endswith("/DESIGN.md"):
            dirs.add(p.split("/")[1])
    dirs = sorted(dirs)
    if not dirs:
        sys.stderr.write("! no design-md/*/DESIGN.md found upstream\n")
        return 3

    known = set()
    if os.path.exists(BRANDS_FILE):
        for r in load_index():
            known.add(r["dir"])
    missing = [d for d in dirs if d not in known]

    if not missing:
        print("up to date: %d brands upstream, %d in index" % (len(dirs), len(known)))
        return 0

    lines = ["| dir | display | category | style | aliases |"]
    for d in missing:
        display = re.sub(r"[.\-_]", " ", d).title()
        lines.append("| %s | %s | uncategorized | TODO | %s |" % (d, display, d.replace("-", " ")))
    block = "\n".join(lines)

    if args.stdout:
        print(block)
        return 0
    if args.write:
        with open(BRANDS_FILE, "a", encoding="utf-8") as fh:
            fh.write("\n" + block + "\n")
        print("appended %d row(s) to %s" % (len(missing), BRANDS_FILE))
        return 0
    print("%d new brand(s) upstream:\n" % len(missing))
    print(block)
    print("\n(re-run with --stdout or --write)")
    return 0


def cmd_mirrors(args):
    data = load_mirrors()
    print(json.dumps(data, ensure_ascii=False, indent=2))
    print("\nconfig file: %s" % MIRRORS_FILE)
    return 0


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #

def build_parser():
    p = argparse.ArgumentParser(
        prog="design_md.py",
        description="Fetch and apply DESIGN.md design systems (VoltAgent/awesome-design-md)")
    sub = p.add_subparsers(dest="cmd")

    sp = sub.add_parser("list", help="list brands (offline)")
    sp.add_argument("--category", help="filter by category slug")
    sp.add_argument("--format", choices=["table", "names", "json"], default="table")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("search", help="search brands by vibe or name (offline)")
    sp.add_argument("query")
    sp.add_argument("--top", type=int, default=5)
    sp.add_argument("--json", action="store_true")
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("fetch", help="fetch a brand DESIGN.md")
    sp.add_argument("brand")
    sp.add_argument("--tokens-only", action="store_true")
    sp.add_argument("--css-vars", action="store_true")
    sp.add_argument("--section", help="comma-separated canonical section keys")
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--raw", action="store_true", help="print the whole document")
    sp.add_argument("--out", help="write the raw document to this path")
    sp.add_argument("--max-chars", type=int, default=20000)
    sp.set_defaults(func=cmd_fetch)

    sp = sub.add_parser("contrast", help="WCAG contrast ratio between two hex colors")
    sp.add_argument("fg")
    sp.add_argument("bg")
    sp.set_defaults(func=cmd_contrast)

    sp = sub.add_parser("lint", help="validate a locally written DESIGN.md")
    sp.add_argument("path")
    sp.set_defaults(func=cmd_lint)

    sp = sub.add_parser("probe-site", help="collect objective design evidence from a URL")
    sp.add_argument("url")
    sp.add_argument("--max-css", type=int, default=6)
    sp.add_argument("--json", action="store_true")
    sp.add_argument("--max-chars", type=int, default=8000)
    sp.set_defaults(func=cmd_probe_site)

    sp = sub.add_parser("sync-brands", help="diff local brand index against upstream")
    sp.add_argument("--stdout", action="store_true")
    sp.add_argument("--write", action="store_true")
    sp.set_defaults(func=cmd_sync_brands)

    sp = sub.add_parser("mirrors", help="show fetch source configuration")
    sp.set_defaults(func=cmd_mirrors)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "cmd", None):
        parser.print_help()
        return 1
    try:
        return args.func(args)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write("! unexpected error: %r\n" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
