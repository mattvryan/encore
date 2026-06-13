# Encore

Sync your Apple Music library and playlists across Macs via Dropbox.

## Requirements

- macOS 13+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.12+
- Apple Music with Automation permission granted to Encore
- Shared Dropbox music folder on each Mac

## Setup

```bash
git clone <repo-url> encore
cd encore
make install
```

This creates a virtual environment, installs dependencies, and registers git hooks.

## Development

Run the menu bar app:

```bash
uv sync
uv run encore
```

| Command | Description |
|---------|-------------|
| `make sync` | Install/update dependencies |
| `make lint` | Run ruff linter and format checker |
| `make format` | Auto-format and fix lint issues |
| `make test` | Run pytest |
| `make check` | Run lint + tests |
| `make commit` | Create a conventional commit (Commitizen) |

### Linting

[Ruff](https://docs.astral.sh/ruff/) handles linting and formatting. Configuration lives in `pyproject.toml`.

### Pre-commit hooks

On every commit, hooks automatically run:

1. **ruff** — lint and format staged Python files
2. **pytest** — full test suite
3. **commitizen** — validate conventional commit message format

Run hooks manually against all files:

```bash
uv run pre-commit run --all-files
```

### Conventional commits

Commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) spec (e.g. `feat: add playlist sync`, `fix: handle missing track`).

Use Commitizen for guided commits:

```bash
make commit
# or
uv run cz commit
```

Examples of valid messages:

```
feat: add folder watcher for music root
fix: retry playlist sync when track is missing
chore: update dependencies
docs: add setup instructions
```
