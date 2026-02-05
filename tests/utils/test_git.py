import subprocess
import unittest
from pathlib import Path
from unittest import mock

from ctfcli.utils.git import check_if_dir_is_inside_git_repo, resolve_repo_url


class TestResolveRepoUrl(unittest.TestCase):
    def test_parses_branch_from_https_url(self):
        with mock.patch("ctfcli.utils.git.subprocess.check_output") as mock_check_output:
            url, branch = resolve_repo_url("https://github.com/user/repo.git@develop")

            self.assertEqual("https://github.com/user/repo.git", url)
            self.assertEqual("develop", branch)
            mock_check_output.assert_not_called()

    def test_parses_branch_from_ssh_url(self):
        with mock.patch("ctfcli.utils.git.subprocess.check_output") as mock_check_output:
            url, branch = resolve_repo_url("git@github.com:user/repo.git@develop")

            self.assertEqual("git@github.com:user/repo.git", url)
            self.assertEqual("develop", branch)
            mock_check_output.assert_not_called()

    def test_explicit_branch_overrides_inline(self):
        with mock.patch("ctfcli.utils.git.subprocess.check_output") as mock_check_output:
            url, branch = resolve_repo_url("https://github.com/user/repo.git@inline", branch="explicit")

            self.assertEqual("https://github.com/user/repo.git", url)
            self.assertEqual("explicit", branch)
            mock_check_output.assert_not_called()

    def test_explicit_branch_with_no_inline(self):
        with mock.patch("ctfcli.utils.git.subprocess.check_output") as mock_check_output:
            url, branch = resolve_repo_url("https://github.com/user/repo.git", branch="develop")

            self.assertEqual("https://github.com/user/repo.git", url)
            self.assertEqual("develop", branch)
            mock_check_output.assert_not_called()

    def test_detects_head_branch_when_none_specified(self):
        # example output taken from ctfcli repo
        mock_output = b"""
ref: refs/heads/master  HEAD
7b4a09af8414eb1f5f6da9a8422fb53b5e9cbc15        HEAD
0370595efd5e9a211b05c55778fc4c0ae2fe70af        refs/heads/15-blank-challenge-template
"""
        with mock.patch("ctfcli.utils.git.subprocess.check_output", return_value=mock_output) as mock_check_output:
            url, branch = resolve_repo_url("https://github.com/CTFd/ctfcli.git")

            self.assertEqual("https://github.com/CTFd/ctfcli.git", url)
            self.assertEqual("master", branch)
            mock_check_output.assert_called_once_with(
                ["git", "ls-remote", "--symref", "https://github.com/CTFd/ctfcli.git", "HEAD"],
                stderr=subprocess.DEVNULL,
            )

    def test_detects_head_branch_for_ssh_url(self):
        mock_output = b"ref: refs/heads/main  HEAD\nabc123  HEAD\n"

        with mock.patch("ctfcli.utils.git.subprocess.check_output", return_value=mock_output) as mock_check_output:
            url, branch = resolve_repo_url("git@github.com:user/repo.git")

            self.assertEqual("git@github.com:user/repo.git", url)
            self.assertEqual("main", branch)
            mock_check_output.assert_called_once_with(
                ["git", "ls-remote", "--symref", "git@github.com:user/repo.git", "HEAD"],
                stderr=subprocess.DEVNULL,
            )

    def test_trailing_at_falls_through_to_head_detection(self):
        mock_output = b"ref: refs/heads/main  HEAD\nabc123  HEAD\n"

        with mock.patch("ctfcli.utils.git.subprocess.check_output", return_value=mock_output) as mock_check_output:
            url, branch = resolve_repo_url("https://github.com/user/repo.git@")

            self.assertEqual("https://github.com/user/repo.git", url)
            self.assertEqual("main", branch)
            mock_check_output.assert_called_once()

    def test_returns_none_if_repository_not_found(self):
        with mock.patch("ctfcli.utils.git.subprocess.check_output") as mock_check_output:
            mock_check_output.side_effect = subprocess.CalledProcessError(128, [])
            url, branch = resolve_repo_url("https://github.com/example/does-not-exist.git")

            self.assertEqual("https://github.com/example/does-not-exist.git", url)
            self.assertIsNone(branch)

    def test_returns_none_if_head_not_set(self):
        with mock.patch("ctfcli.utils.git.subprocess.check_output", return_value=b"") as mock_check_output:
            url, branch = resolve_repo_url("https://github.com/example/no-head.git")

            self.assertEqual("https://github.com/example/no-head.git", url)
            self.assertIsNone(branch)
            mock_check_output.assert_called_once()

    def test_returns_none_for_non_git_path_without_subprocess(self):
        with mock.patch("ctfcli.utils.git.subprocess.check_output") as mock_check_output:
            url, branch = resolve_repo_url("some/local/path")

            self.assertEqual("some/local/path", url)
            self.assertIsNone(branch)
            mock_check_output.assert_not_called()


class TestCheckIfDirIsInsideGitRepo(unittest.TestCase):
    def test_returns_true_if_inside_git_repo(self):
        mock_output = b"true\n"

        with mock.patch("ctfcli.utils.git.subprocess.check_output", return_value=mock_output) as mock_check_output:
            inside_git_repo = check_if_dir_is_inside_git_repo()

            mock_check_output.assert_called_once_with(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=None,
                stderr=subprocess.DEVNULL,
            )
            self.assertTrue(inside_git_repo)

    def test_accepts_cwd(self):
        mock_output = b"true\n"

        with mock.patch("ctfcli.utils.git.subprocess.check_output", return_value=mock_output) as mock_check_output:
            cwd_path = Path("/tmp/test/ctfcli/test-challenges-dir")
            inside_git_repo = check_if_dir_is_inside_git_repo(cwd_path)

            mock_check_output.assert_called_once_with(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=cwd_path,
                stderr=subprocess.DEVNULL,
            )
            self.assertTrue(inside_git_repo)

        with mock.patch("ctfcli.utils.git.subprocess.check_output", return_value=mock_output) as mock_check_output:
            cwd_path = "/tmp/test/ctfcli/test-challenges-dir"
            inside_git_repo = check_if_dir_is_inside_git_repo(cwd_path)

            mock_check_output.assert_called_once_with(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=cwd_path,
                stderr=subprocess.DEVNULL,
            )
            self.assertTrue(inside_git_repo)

    def test_returns_false_if_outside_git_repo(self):
        mock_output = b"fatal: not a git repository (or any of the parent directories): .git\n"

        with mock.patch("ctfcli.utils.git.subprocess.check_output", return_value=mock_output) as mock_check_output:
            inside_git_repo = check_if_dir_is_inside_git_repo()

            mock_check_output.assert_called_once_with(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=None,
                stderr=subprocess.DEVNULL,
            )
            self.assertFalse(inside_git_repo)

    def test_returns_false_if_subprocess_raises(self):
        with mock.patch("ctfcli.utils.git.subprocess.check_output") as mock_check_output:
            mock_check_output.side_effect = subprocess.CalledProcessError(128, [])
            inside_git_repo = check_if_dir_is_inside_git_repo()

            mock_check_output.assert_called_once_with(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=None,
                stderr=subprocess.DEVNULL,
            )
            self.assertFalse(inside_git_repo)
