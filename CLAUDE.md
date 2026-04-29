

<!-- stash-context -->
## Stash

This repo uses [Stash](https://joinstash.ai) for shared agent history.
Your coding agent has the `stash` CLI on its PATH. Run `stash --help` to see commands.

Common reads (all support `--json`):
- `stash history search "<query>"` — full-text search across transcripts
- `stash history query --limit 20` — latest events
- `stash history agents` — who's been active
- `stash notebooks list --all` — shared notebooks
