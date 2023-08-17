import subprocess
import unittest
from pathlib import Path
from unittest import mock

from ctfcli.utils.git import check_if_dir_is_inside_git_repo, get_git_repo_head_branch


class TestGetGitRepoHeadBranch(unittest.TestCase):
    def test_gets_head_branch_if_head_exists(self):
        # example output taken from ctfcli repo
        mock_output = b"""
ref: refs/heads/master  HEAD
7b4a09af8414eb1f5f6da9a8422fb53b5e9cbc15        HEAD
0370595efd5e9a211b05c55778fc4c0ae2fe70af        refs/heads/15-blank-challenge-template
410d49503971cf0e16b29a1707b52d911945a59f        refs/heads/21-add-deploy-functionality
ca1f8be5c207e911a3110f1e0223a1f3db9aa269        refs/heads/30-writeup-folder
2f12163e6c6a4d105bd5e4ac25167fac8c6f5168        refs/heads/32-add-flag-data-into-spec
58270ef683a3f92c4beffc3528e1188e11ddb04f        refs/heads/46-install-state-simplified
4d0e530edd08baebccafb71b6b613c49b67458bd        refs/heads/47-topics
47cb2285604da69c9e5c9b6cd9b59a9b9c50b647        refs/heads/70-pages-support
c75b674c1b582852f18719b08b474515d138a14d        refs/heads/75-challenge-healthcheck
"""
        with mock.patch("ctfcli.utils.git.subprocess.check_output", return_value=mock_output) as mock_check_output:
            expected_head_branch = "master"
            head_branch = get_git_repo_head_branch("https://github.com/CTFd/ctfcli")

            mock_check_output.assert_called_once_with(
                [
                    "git",
                    "ls-remote",
                    "--symref",
                    "https://github.com/CTFd/ctfcli",
                    "HEAD",
                ],
                stderr=subprocess.DEVNULL,
            )
            self.assertEqual(expected_head_branch, head_branch)

    def test_returns_none_if_repository_not_found(self):
        with mock.patch("ctfcli.utils.git.subprocess.check_output") as mock_check_output:
            mock_check_output.side_effect = subprocess.CalledProcessError(128, [])
            head_branch = get_git_repo_head_branch("https://github.com/example/does-not-exist")

            mock_check_output.assert_called_once_with(
                [
                    "git",
                    "ls-remote",
                    "--symref",
                    "https://github.com/example/does-not-exist",
                    "HEAD",
                ],
                stderr=subprocess.DEVNULL,
            )
            self.assertIsNone(head_branch)

    def test_returns_none_if_head_not_found(self):
        mock_output = b""

        with mock.patch("ctfcli.utils.git.subprocess.check_output", return_value=mock_output) as mock_check_output:
            head_branch = get_git_repo_head_branch("https://github.com/example/does-not-have-a-head-branch")

            mock_check_output.assert_called_once_with(
                [
                    "git",
                    "ls-remote",
                    "--symref",
                    "https://github.com/example/does-not-have-a-head-branch",
                    "HEAD",
                ],
                stderr=subprocess.DEVNULL,
            )
            self.assertIsNone(head_branch)


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
