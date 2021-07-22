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
