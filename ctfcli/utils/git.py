import subprocess
from os import PathLike
from typing import Optional, Union


def get_git_repo_head_branch(repo: str) -> Optional[str]:
    """
    A helper method to get the reference of the HEAD branch of a git remote repo.
    https://stackoverflow.com/a/41925348
    """
    try:
        output = subprocess.check_output(["git", "ls-remote", "--symref", repo, "HEAD"], stderr=subprocess.DEVNULL)

        # if for some reason subprocess didn't error, but returned None or an empty byte-string - return None
        # this can happen if a repository exists, but doesn't have a head branch
        if type(output) != bytes or len(output) == 0:
            return None

    except subprocess.CalledProcessError:
        return None

    # otherwise process the output
    output = output.decode().strip()
    head_branch_line = output.split()[1]
    if head_branch_line.startswith("refs/heads/"):
        return head_branch_line[11:]


def check_if_dir_is_inside_git_repo(cwd: Optional[Union[str, PathLike]] = None) -> bool:
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

        if out == "true":
            return True

        return False
    except subprocess.CalledProcessError:
        return False
