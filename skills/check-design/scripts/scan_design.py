#!/usr/bin/env python3
"""Deterministic design-system drift scan for a web frontend.

Usage (run from anywhere inside the repo):
    python3 -I ~/.claude/skills/check-design/scripts/scan_design.py <paths...>
    python3 -I ~/.claude/skills/check-design/scripts/scan_design.py --summary <frontend src dir>   # counts only
    python3 -I ~/.claude/skills/check-design/scripts/scan_design.py --config <design-scan.json> <paths...>

Without --config it uses ~/.claude/project-profiles/<repo>/design-scan.json if that exists,
otherwise generic defaults. Output is evidence for a human/agent reviewer, not a verdict:
every hit still needs judgment (see SKILL.md).

design-scan.json (all keys optional):
  palette_files   files whose hex colours are the palette, relative to the repo root.
                  Default: every tailwind.config.* plus CSS files named index/globals/global/
                  app/theme/tokens/variables.css (node_modules, dist and build skipped).
  extensions      file types to scan. Default: .tsx .ts .jsx .js .vue .svelte
  token_hint      what to use instead of raw hex, shown in the rule text (e.g. "ink-*, mint-*")
  radius_tokens   {"px": "class"}: arbitrary radii equal to a token are reported as radius-token,
                  others as radius-off-scale. Without it every arbitrary radius is radius-arbitrary.
  type_scale      allowed px sizes for text-[Npx]. Without it every arbitrary size is type-arbitrary.
  icon_prefix     the Iconify prefix the project uses (e.g. "heroicons"); icons from other sets
                  are reported. Without it the icon rule is skipped.
  inline_card     {"all": [regex, ...], "use": ".card"}: a line matching every regex re-declares
                  the card component inline. Without it the rule is skipped.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HEX = re.compile(r"#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b")
SKIP_DIRS = {"node_modules", "dist", "build", ".next", ".nuxt", ".svelte-kit", "coverage", ".git"}
PALETTE_CSS_NAMES = {"index.css", "globals.css", "global.css", "app.css", "theme.css", "tokens.css", "variables.css"}
DEFAULT_EXTENSIONS = [".tsx", ".ts", ".jsx", ".js", ".vue", ".svelte"]
PROFILES = Path.home() / ".claude" / "project-profiles"


def git(*args):
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def repo_root():
    top = git("rev-parse", "--show-toplevel")
    return Path(top) if top else Path.cwd()


def repo_name():
    remote = git("remote", "get-url", "origin")
    if remote:
        return re.sub(r"\.git$", "", remote.rstrip("/").split("/")[-1].split(":")[-1])
    common = git("rev-parse", "--path-format=absolute", "--git-common-dir")
    return Path(common).parent.name if common else Path.cwd().name


def load_config(path):
    if path:
        return json.loads(Path(path).read_text(encoding="utf-8")), path
    profile = PROFILES / repo_name() / "design-scan.json"
    if profile.exists():
        return json.loads(profile.read_text(encoding="utf-8")), str(profile)
    return {}, None


def walk(root, max_depth):
    def visit(directory, depth):
        try:
            entries = sorted(directory.iterdir())
        except OSError:
            return
        for entry in entries:
            if entry.is_dir():
                if entry.name not in SKIP_DIRS and not entry.name.startswith(".") and depth < max_depth:
                    yield from visit(entry, depth + 1)
            else:
                yield entry
    yield from visit(root, 0)


def palette_files(root, config):
    if "palette_files" in config:
        return [root / p for p in config["palette_files"]]
    return [f for f in walk(root, 5) if f.name.startswith("tailwind.config.") or f.name in PALETTE_CSS_NAMES]


def palette(files):
    allowed = set()
    for path in files:
        if path.exists():
            allowed |= {h.lower() for h in HEX.findall(path.read_text(encoding="utf-8", errors="replace"))}
    return allowed


def iter_files(paths, extensions):
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.suffix in extensions and not SKIP_DIRS.intersection(f.parts):
                    yield f


class Scanner:
    def __init__(self, config, allowed):
        self.allowed = allowed
        self.radius_tokens = {int(k): v for k, v in config.get("radius_tokens", {}).items()}
        self.type_scale = set(config.get("type_scale", []))
        self.icon_prefix = config.get("icon_prefix")
        card = config.get("inline_card") or {}
        self.card_patterns = [re.compile(p) for p in card.get("all", [])]
        hint = config.get("token_hint")
        scale = "/".join(str(n) for n in sorted(self.type_scale))

        self.rules = {}
        if allowed:
            self.rules["off-palette-hex"] = "Hex colour not in the palette files"
            self.rules["raw-hex"] = "Hex colour hard-coded in a class or style; prefer the token" + (f" ({hint})" if hint else "")
        if self.radius_tokens:
            self.rules["radius-token"] = "Arbitrary radius that equals a token; use the token class"
            self.rules["radius-off-scale"] = "Arbitrary radius not on the radius scale"
        else:
            self.rules["radius-arbitrary"] = "Arbitrary radius; check it against the radius scale"
        if self.type_scale:
            self.rules["type-off-scale"] = f"Arbitrary font size not on the type scale ({scale})"
        else:
            self.rules["type-arbitrary"] = "Arbitrary font size; check it against the type scale"
        self.rules["arbitrary-z"] = "Arbitrary z-index; use a shared z scale"
        self.rules["outline-none"] = "outline-none without a focus-visible/ring replacement on the same element"
        self.rules["click-div"] = "onClick on a div/span; use <button> or <a>"
        if self.icon_prefix:
            self.rules["icon-set"] = f"Icon from a different set than {self.icon_prefix}"
        self.rules["three-dots"] = 'Literal "..." in UI text; use the ellipsis character'
        self.rules["h-screen"] = "h-screen; prefer min-h-dvh / h-dvh"
        if self.card_patterns:
            self.rules["inline-card"] = f"Card styling re-declared inline; use {card.get('use', 'the card component')}"

    def scan_line(self, line):
        hits = []
        if self.allowed:
            for h in HEX.findall(line):
                if h.lower() not in self.allowed:
                    hits.append(("off-palette-hex", h))
                elif "className" in line or "style" in line or "-[" in line:
                    hits.append(("raw-hex", h))
        for px in re.findall(r"rounded(?:-[trbl]{1,2})?-\[(\d+)px\]", line):
            n = int(px)
            if not self.radius_tokens:
                hits.append(("radius-arbitrary", f"{n}px"))
            elif n in self.radius_tokens:
                hits.append(("radius-token", f"{n}px -> {self.radius_tokens[n]}"))
            else:
                hits.append(("radius-off-scale", f"{n}px"))
        for px in re.findall(r"text-\[(\d+)px\]", line):
            if not self.type_scale:
                hits.append(("type-arbitrary", f"{px}px"))
            elif int(px) not in self.type_scale:
                hits.append(("type-off-scale", f"{px}px"))
        for z in re.findall(r"\bz-\[(\d+)\]", line):
            hits.append(("arbitrary-z", z))
        if "outline-none" in line and not re.search(r"focus-visible:|focus:ring|focus:outline|focus-within:", line):
            hits.append(("outline-none", ""))
        if re.search(r"<(div|span)\b[^>]*(\bonClick|@click|\bon:click)=", line):
            hits.append(("click-div", ""))
        if self.icon_prefix:
            for prefix in re.findall(r'icon="([a-z-]+):', line):
                if not prefix.startswith(self.icon_prefix):
                    hits.append(("icon-set", prefix))
        if re.search(r"[A-Za-z]\.\.\.(?=[\"'`<\s]|$)", line):
            hits.append(("three-dots", ""))
        if "h-screen" in line:
            hits.append(("h-screen", ""))
        if self.card_patterns and all(p.search(line) for p in self.card_patterns):
            hits.append(("inline-card", ""))
        return hits


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--summary", action="store_true", help="only print counts per rule")
    parser.add_argument("--config", help="design-scan.json (default: the project profile's, if any)")
    args = parser.parse_args()

    root = repo_root()
    config, config_source = load_config(args.config)
    files = palette_files(root, config)
    allowed = palette(files)
    scanner = Scanner(config, allowed)
    extensions = set(config.get("extensions", DEFAULT_EXTENSIONS))

    found = defaultdict(list)
    for f in iter_files(args.paths, extensions):
        for number, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for rule, detail in scanner.scan_line(line):
                shown = f.relative_to(root) if f.is_absolute() and f.is_relative_to(root) else f
                found[rule].append((shown, number, detail))

    if not found:
        print("No drift found in the scanned files (this covers only the rules below, not visual quality).")
    for rule, text in scanner.rules.items():
        hits = found.get(rule)
        if not hits:
            continue
        print(f"\n## {rule} ({len(hits)}): {text}")
        if args.summary:
            continue
        for path, number, detail in hits[:60]:
            print(f"  {path}:{number}" + (f"  {detail}" if detail else ""))
        if len(hits) > 60:
            print(f"  ... {len(hits) - 60} more")
    print("\nRules checked:", ", ".join(scanner.rules))
    print("Config:", config_source or "none (generic defaults)")
    if allowed:
        print("Palette from:", ", ".join(str(p.relative_to(root)) if p.is_relative_to(root) else str(p) for p in files if p.exists()))
    else:
        print("Palette: no palette files found, so colour rules were skipped. Pass palette_files in a config.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
