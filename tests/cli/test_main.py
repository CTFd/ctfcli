import contextlib
import io
import unittest

import fire

from ctfcli import __main__ as ctfcli


class TestCLIEntrypoint(unittest.TestCase):
    def test_loads_challenge_command(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            fire.Fire(ctfcli.CTFCLI, ["challenge"])

        # fmt: off
        expected_commands = [
            "add", "deploy", "edit", "healthcheck",
            "install", "lint", "new", "pull", "push",
            "restore", "show", "sync", "templates",
            "view",
        ]
        # fmt: on

        stdout = stdout.getvalue()
        for command in expected_commands:
            self.assertIn(command, stdout)

    def test_loads_config_command(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            fire.Fire(ctfcli.CTFCLI, ["config"])

        expected_commands = ["edit", "path", "show", "view"]

        stdout = stdout.getvalue()
        for command in expected_commands:
            self.assertIn(command, stdout)

    def test_loads_pages_command(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            fire.Fire(ctfcli.CTFCLI, ["pages"])

        expected_commands = ["pull", "push", "sync"]

        stdout = stdout.getvalue()
        for command in expected_commands:
            self.assertIn(command, stdout)

    def test_loads_plugins_command(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            fire.Fire(ctfcli.CTFCLI, ["plugins"])

        expected_commands = ["dir", "install", "list", "path", "uninstall"]

        stdout = stdout.getvalue()
        for command in expected_commands:
            self.assertIn(command, stdout)

    def test_loads_templates_command(self):
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            fire.Fire(ctfcli.CTFCLI, ["templates"])

        expected_commands = ["dir", "install", "list", "path", "uninstall"]

        stdout = stdout.getvalue()
        for command in expected_commands:
            self.assertIn(command, stdout)
