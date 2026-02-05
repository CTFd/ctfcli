import subprocess
from os import PathLike


def resolve_repo_url(repo: str, branch: str | None = None) -> tuple[str, str | None]:
    """
    Resolves a repo string to (clean_url, branch).

    Resolution order:
      1. The `branch` parameter, if provided
      2. An inline @branch parsed from the repo string
      3. The remote's HEAD branch, detected via git ls-remote

    Returns (url, None) if no branch can be determined.
    """
    # Strip an inline @branch suffix if present
    marker = ".git@"
    idx = repo.rfind(marker)
    if idx != -1:
        inline_branch = repo[idx + 5 :]
        repo = repo[: idx + 4]  # clean URL up to .git
        if not branch and inline_branch:
            branch = inline_branch

    # Branch already resolved
    if branch:
        return repo, branch

    # Non-git paths have no remote to query
    if not repo.endswith(".git"):
        return repo, None

    # Fall back to detecting the remote HEAD branch
    # https://stackoverflow.com/a/41925348
    try:
        output = subprocess.check_output(
            ["git", "ls-remote", "--symref", repo, "HEAD"],
            stderr=subprocess.DEVNULL,
        )

        # repo exists but doesn't have a head branch
        if type(output) != bytes or len(output) == 0:
            return repo, None

    except subprocess.CalledProcessError:
        return repo, None

    output = output.decode().strip()
    head_branch_line = output.split()[1]
    if head_branch_line.startswith("refs/heads/"):
        return repo, head_branch_line[11:]

    return repo, None


def check_if_git_subrepo_is_installed() -> bool:
    output = subprocess.run(["git", "subrepo"], capture_output=True, text=True)
    return "git: 'subrepo' is not a git command" not in output.stderr


def check_if_dir_is_inside_git_repo(cwd: str | PathLike | None = None) -> bool:
    """
    Checks whether a given directory is inside a git repo.
    """
    try:
        out = (
            subprocess.check_output(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=cwd,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )

        return out == "true"
    except subprocess.CalledProcessError:
        return False
