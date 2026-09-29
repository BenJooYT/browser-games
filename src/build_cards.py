#!/usr/bin/env python3
"""Hub card generator for the browser-games site.

Reads every game.json manifest in the games repo checkout and renders the
game cards + counts into the hub page. New games appear automatically on the
next deploy — no manual card edits.

Usage:
    build_cards.py <games-root> <hub-html>

- <games-root>: checkout of CursedOne0u0/local-browser-games
               (contains the local-browser-games/ dir).
- <hub-html>:   hub page to patch IN PLACE. It must contain the placeholders
               <!--CARDS:playable-->, <!--CARDS:lan--> and the tokens
               {{META_DESC}}, {{LEDE_TOTAL}}, {{N_PLAYABLE}}, {{N_LAN}}.

Manifest schema (game.json, next to the game):
    title, emoji, kind ("playable"|"lan"), blurb, keys (HTML allowed —
    manifests are trusted, same org), dir (relative to local-browser-games/),
    entry (linked file: index.html for playable, README.md for lan),
    players (playable tag text, e.g. "Solo"), port (lan only),
    screenshot (optional; missing file or key -> emoji placeholder),
    order (sort key within section).

Any invalid manifest fails the build loudly so a deploy never ships a
half-built hub.
"""

import glob
import html
import json
import os
import sys

BASE = "games/local-browser-games"  # hub-relative prefix of the games checkout


def esc(s):
    return html.escape(str(s), quote=True)


def shot(g):
    """Screenshot <img> (or emoji placeholder when the game has none)."""
    rel = g.get("screenshot")
    if rel:
        disk = os.path.join(GAMES_DISK, g["dir"], rel)
        if not os.path.isfile(disk):
            raise SystemExit(f"ERROR: {g['dir']}/game.json declares missing screenshot {rel}")
        src = f"{BASE}/{g['dir']}/{rel}"
        return (f'<img class="shot" src="{esc(src)}" width="1000" height="800" '
                f'alt="" loading="lazy" decoding="async">')
    return f'<div class="shot ph" aria-hidden="true"><span>{esc(g["emoji"])}</span></div>'


def playable_card(g):
    href = f'{BASE}/{g["dir"]}/{g["entry"]}'
    img = shot(g)
    if img.startswith("<img"):
        img = (f'<a href="{esc(href)}" tabindex="-1" aria-hidden="true">\n        {img}\n      </a>')
    return f"""<article class="card">
      {img}
      <div class="body">
        <div class="title"><h3>{esc(g["emoji"])} {esc(g["title"])}</h3><span class="tag">{esc(g["players"])}</span></div>
        <p class="blurb">{g["blurb"]}</p>
        <p class="keys">{g["keys"]}</p>
        <p class="cta"><a class="btn" href="{esc(href)}">▶ Play {esc(g["title"])}</a></p>
      </div>
    </article>"""


def lan_card(g):
    href = f'{BASE}/{g["dir"]}/{g["entry"]}'
    return f"""<article class="card lan">
      {shot(g)}
      <div class="body">
        <div class="title"><h3>{esc(g["emoji"])} {esc(g["title"])}</h3><span class="tag lan">LAN · :{int(g["port"])}</span></div>
        <p class="blurb">{g["blurb"]}</p>
        <p class="keys">{g["keys"]}</p>
        <p class="cta"><a class="btn ghost" href="{esc(href)}">How to run</a></p>
      </div>
    </article>"""


def load_games(games_root):
    global GAMES_DISK
    inner = os.path.join(games_root, "local-browser-games")
    if not os.path.isdir(inner):
        raise SystemExit(f"ERROR: {inner} not found — wrong games-root?")
    GAMES_DISK = inner
    games = []
    for path in sorted(glob.glob(os.path.join(inner, "*", "*", "game.json"))):
        rel = os.path.relpath(path, inner)
        try:
            with open(path, encoding="utf-8") as f:
                g = json.load(f)
        except Exception as e:
            raise SystemExit(f"ERROR: {rel} is not valid JSON: {e}")
        req = ["title", "emoji", "kind", "blurb", "keys", "dir", "entry", "order"]
        for k in req:
            if k not in g or g[k] in ("", None):
                raise SystemExit(f"ERROR: {rel} missing required field {k!r}")
        if g["kind"] not in ("playable", "lan"):
            raise SystemExit(f"ERROR: {rel} has unknown kind {g['kind']!r}")
        if g["kind"] == "playable" and "players" not in g:
            raise SystemExit(f"ERROR: {rel} playable game needs a 'players' tag")
        if g["kind"] == "lan" and "port" not in g:
            raise SystemExit(f"ERROR: {rel} lan game needs a 'port'")
        gdir = os.path.join(inner, g["dir"])
        if not os.path.isdir(gdir):
            raise SystemExit(f"ERROR: {rel} points at missing dir {g['dir']}")
        if not os.path.isfile(os.path.join(gdir, g["entry"])):
            raise SystemExit(f"ERROR: {rel} entry file {g['entry']} not found")
        g["_manifest"] = rel
        games.append(g)
    if not games:
        raise SystemExit("ERROR: no game.json manifests found")
    return games


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_cards.py <games-root> <hub-html>")
    games_root, hub_path = sys.argv[1], sys.argv[2]
    games = load_games(games_root)
    playable = sorted([g for g in games if g["kind"] == "playable"],
                      key=lambda g: (g["order"], g["title"]))
    lan = sorted([g for g in games if g["kind"] == "lan"],
                 key=lambda g: (g["order"], g["title"]))

    with open(hub_path, encoding="utf-8") as f:
        page = f.read()
    for token in ("<!--CARDS:playable-->", "<!--CARDS:lan-->",
                  "{{META_DESC}}", "{{LEDE_TOTAL}}", "{{N_PLAYABLE}}", "{{N_LAN}}"):
        if token not in page:
            raise SystemExit(f"ERROR: hub template missing placeholder {token}")

    names = [g["title"] for g in playable]
    if len(names) > 1:
        desc = "Play " + ", ".join(names[:-1]) + " and " + names[-1] + " instantly in your browser. No download, no install."
    else:
        desc = f"Play {names[0]} instantly in your browser. No download, no install."

    def indent(block):
        return "\n\n".join("    " + c.replace("\n", "\n    ") for c in block)

    page = page.replace("<!--CARDS:playable-->",
                        indent(playable_card(g) for g in playable))
    page = page.replace("<!--CARDS:lan-->",
                        indent(lan_card(g) for g in lan))
    page = page.replace("{{META_DESC}}", esc(desc))
    page = page.replace("{{LEDE_TOTAL}}", str(len(games)))
    page = page.replace("{{N_PLAYABLE}}", str(len(playable)))
    page = page.replace("{{N_LAN}}", str(len(lan)))

    with open(hub_path, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"hub: {len(playable)} playable ({', '.join(names)}), "
          f"{len(lan)} lan ({', '.join(g['title'] for g in lan)})")


if __name__ == "__main__":
    main()
