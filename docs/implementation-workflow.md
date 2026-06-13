# Implementation Workflow

Rules for implementing [Encore](superpowers/plans/2026-06-12-encore.md) one task at a time.

## Scope

- Work **one task at a time**.
- Complete **all steps of a task** in a single branch and PR.
- Do not batch multiple tasks into one PR.

## Before starting a task

1. Check out `main` and sync with origin:

   ```bash
   git checkout main
   git pull origin main
   ```

2. Create a new branch from `main`:

   ```text
   impl-task-<task-number>
   ```

   Example: `impl-task-4`, `impl-task-5`

## Implementation

1. Implement the full task from the plan — tests, implementation, and any docs updates described in that task.
2. **Add or update tests** for every new behavior or module. Keep test coverage strong as the codebase grows.
3. Run checks locally before committing:

   ```bash
   make check          # lint + test
   # or individually:
   make lint
   make test
   ```

4. Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages (`feat:`, `fix:`, `test:`, `chore:`, etc.). `make commit` runs Commitizen.

## After implementing a task

When lint and tests pass:

1. Commit the changes.
2. Push the branch to origin.
3. Open a pull request against `main`.
4. Wait for CI to pass.
5. Stop and wait for review — do not start the next task until the PR is merged.

## Pull requests

- One PR per task.
- PR title should follow conventional commit style and describe the task (e.g. `feat: add playlist track diff logic (task 4)`).
- PR body should summarize what changed and include a brief test plan.
- **Merged branches are automatically deleted on origin** (GitHub repo setting: *Automatically delete head branches*). After merging, prune stale local branches:

  ```bash
  git checkout main
  git pull origin main
  git fetch --prune
  ```

## CI and pre-commit

- **Pre-commit hooks** (local): ruff lint/format, pytest, conventional commit message validation.
- **GitHub Actions** (on PR): ruff lint/format and pytest on Ubuntu with Python 3.12.

Both must pass before requesting review.

## Notes

- `rumps` is a macOS-only dependency; Linux CI skips it via a platform marker in `pyproject.toml`.
- macOS-specific behavior (AppleScript, Music.app) may need macOS runners or manual verification on a Mac until dedicated macOS CI is added.
