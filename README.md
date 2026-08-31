# alfred-workflow-discogs

Alfred Workflow to browse [Discogs](https://www.discogs.com) via the [Discogs API v2.0](https://www.discogs.com/developers).

## Commands

### `dg <query>` - search the Discogs database

Searches releases, artists, labels, and masters as you type; no Enter needed.

- Enter on a label/artist/master drills into its releases; Enter on a release shows its tracklist.
- Cmd+Enter at any point opens that item's Discogs page directly.

## Install

1. Download the latest `Discogs.alfredworkflow` from [Releases](https://github.com/aleksgorbenko/alfred-workflow-discogs/releases).
2. Double-click it - Alfred will prompt to import.
3. Requires [Alfred](https://www.alfredapp.com) with a Powerpack license.

## Setup

1. Open the workflow in Alfred, click the `[x]` (Configure Workflow) button.
2. Paste your [Discogs personal access token](https://www.discogs.com/settings/developers) into the **Discogs API Token** field (click "Generate new token").

## Development

- Python 3.14, stdlib only.
- `src/dgapi/` - runtime scripts Alfred calls.
- `tools/` - dev-only scripts (bundle verification), not shipped.

```sh
make check    # lint + format check + tests
make build    # package dist/Discogs.alfredworkflow
make verify   # audit the built bundle for local paths, tokens, junk files
make release VERSION=v1.0.0
make sync-plist WORKFLOW_DIR=/path/to/installed/workflow   # pull info.plist edits back
make link-live WORKFLOW_DIR=/path/to/installed/workflow    # symlink src/ for live dev
```

## My Other Workflows

- [WaniKani for Alfred](https://github.com/aleksgorbenko/alfred-workflow-wanikani)
- [2Do for Alfred](https://github.com/aleksgorbenko/alfred-workflow-2do)
- [BunPro for Alfred](https://github.com/aleksgorbenko/alfred-workflow-bunpro)
