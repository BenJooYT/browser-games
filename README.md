# Browser Games — site

GitHub Pages site for [CursedOne0u0/local-browser-games](https://github.com/CursedOne0u0/local-browser-games).

This repo holds **only the site** — the hub page and the deploy workflow. The games
themselves are not copied here. Each deploy checks out the games repo at build time and
assembles it alongside the hub, so a fix in the games repo is all it takes to update the
live site.

## Layout

```
src/index.html                  the hub page
.github/workflows/deploy-pages.yml
```

## How a deploy works

1. `actions/checkout` → this repo, into `site/`
2. `actions/checkout` → the games repo at `ref: main`, into `site/_site/games/`
3. Copy the hub to `site/_site/index.html` and strip the games repo's `.git`/`.github`
4. **Verify** every `games/...` link in the hub exists on disk — a missing file fails the
   build instead of shipping a dead tile
5. Upload and deploy

## Live site

<https://benjooyt.github.io/browser-games/>

## Redeploying after a game change

Push to the site repo, or dispatch the workflow manually. To rebuild straight from a games
commit without touching this repo:

```bash
gh api repos/BenJooYT/browser-games/dispatches \
  -f event_type=games-updated
```

`ref: main` in the workflow is the games branch that gets published — pin it to a tag if
you would rather deploy a specific release.

## Adding a game

Add a tile to `src/index.html` pointing at `games/local-browser-games/...`. If the path is
wrong the deploy fails on the verify step, so a broken tile never reaches production.
