from pathlib import Path

import click

GITHUB_ACTIONS_SYNC_WORKFLOW = """\
name: Sync challenges to CTFd

on:
  push:
    branches:
      - main
      - master

jobs:
  sync:
    # Only run on the repository's default branch
    if: github.ref == format('refs/heads/{0}', github.event.repository.default_branch)
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.x"

      - name: Install ctfcli
        run: pip install ctfcli

      - name: Install challenges to CTFd
        run: ctf challenge install --force
"""


def create_github_integration(project_path: Path) -> list[str]:
    workflows_dir = project_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    (workflows_dir / "sync.yml").write_text(GITHUB_ACTIONS_SYNC_WORKFLOW)
    click.secho("Created .github/workflows/sync.yml", fg="green")
    return [".github/workflows/sync.yml"]
