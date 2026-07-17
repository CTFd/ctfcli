from pathlib import Path

import click

GITLAB_CI_SYNC_PIPELINE = """\
sync-challenges:
  image: python:3
  # Only run on the repository's default branch
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
  script:
    - pip install ctfcli
    - ctf challenge install --force
"""


def create_gitlab_integration(project_path: Path) -> list[str]:
    (project_path / ".gitlab-ci.yml").write_text(GITLAB_CI_SYNC_PIPELINE)
    click.secho("Created .gitlab-ci.yml", fg="green")
    return [".gitlab-ci.yml"]
