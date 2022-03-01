import subprocess


def get_git_repo_head_branch(repo):
    """
    A helper method to get the reference of the HEAD branch of a git remote repo.
    https://stackoverflow.com/a/41925348
    """
    out = subprocess.check_output(
        ["git", "ls-remote", "--symref", repo, "HEAD"]
    ).decode()
    head_branch = out.split()[1]
    return head_branch


def check_if_dir_is_inside_git_repo(dir=None):
    """
    Checks whether a given directory is inside of a git repo.
    """
    try:
        out = (
            subprocess.check_output(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=dir,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
        print(out)
        if out == "true":
            return True
        return False
    except subprocess.CalledProcessError:
        return False
