# Implementation Workflow

Rules for implementing [Encore](superpowers/plans/2026-06-12-encore.md) one task (or step) at a time.

## Scope

- Work **one task at a time**.
- If a task has numbered steps, work **one step at a time**.
- Do not batch multiple tasks or steps into a single branch or PR.

## Before starting a task or step

1. Check out `main` and sync with origin:

   ```bash
   git checkout main
   git pull origin main
   ```

2. Create a new branch from `main`:

   | Case | Branch format | Example |
   |------|---------------|---------|
   | Task with steps | `impl-task-<task>-<step>` | `impl-task-1-1`, `impl-task-1-2` |
   | Task without steps | `impl-task-<task>` | `impl-task-7` |

## Implementation

1. Implement only the work described in the current task or step of the plan.
2. **Add or update tests** for every new behavior or module. Keep test coverage strong as the codebase grows.
3. Run checks locally before committing:

   ```bash
   make check          # lint + test
   # or individually:
   make lint
   make test
   ```

4. Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages (`feat:`, `fix:`, `test:`, `chore:`, etc.). `make commit` runs Commitizen.

## After implementing a task or step

When lint and tests pass:

1. Commit the changes.
2. Push the branch to origin.
3. Open a pull request against `main`.
4. Wait for CI to pass.
5. Stop and wait for review — do not start the next task or step until the PR is merged.

## Pull requests

- One PR per task or step.
- PR title should follow conventional commit style and describe the task/step (e.g. `feat: initialize uv project (task 1 step 1)`).
- PR body should summarize what changed and include a brief test plan.

## CI and pre-commit

- **Pre-commit hooks** (local): ruff lint/format, pytest, conventional commit message validation.
- **GitHub Actions** (on PR): ruff lint/format and pytest on Ubuntu with Python 3.12.

Both must pass before requesting review.

## Notes

- `rumps` is a macOS-only dependency; Linux CI skips it via a platform marker in `pyproject.toml`.
- macOS-specific behavior (AppleScript, Music.app) may need macOS runners or manual verification on a Mac until dedicated macOS CI is added.
