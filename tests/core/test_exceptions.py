import unittest
from unittest import mock
from unittest.mock import MagicMock, call

from ctfcli.core.exceptions import LintException


class TestLintException(unittest.TestCase):
    @mock.patch("ctfcli.core.exceptions.click.echo")
    @mock.patch("ctfcli.core.exceptions.click.secho")
    def test_print_summary(self, mock_secho: MagicMock, mock_echo: MagicMock):
        test_issues = {
            "fields": [
                "challenge.yml is missing required field: author",
                "challenge.yml is missing required field: name",
                "challenge.yml is missing required field: value",
            ],
            "dockerfile": ["Dockerfile exists but image field does not point to it", "Dockerfile is missing EXPOSE"],
            "hadolint": ["-:1 DL3006 warning: Always tag the version of an image explicitly"],
            "files": [
                "Challenge file 'files/test-file.png' specified, but not found at /challenge/files/test-file.png"
            ],
        }

        with self.assertRaises(LintException) as e:
            raise LintException(issues=test_issues)

        self.assertDictEqual(test_issues, e.exception.issues)
        e.exception.print_summary()

        mock_secho.assert_has_calls(
            [
                call("Fields:", fg="yellow"),
                call("Dockerfile:", fg="yellow"),
                call("Hadolint:", fg="yellow"),
                call("Files:", fg="yellow"),
            ]
        )

        mock_echo.assert_has_calls(
            [
                call(" - challenge.yml is missing required field: author"),
                call(" - challenge.yml is missing required field: name"),
                call(" - challenge.yml is missing required field: value"),
                call(),
                call(" - Dockerfile exists but image field does not point to it"),
                call(" - Dockerfile is missing EXPOSE"),
                call(),
                call("-:1 DL3006 warning: Always tag the version of an image explicitly"),
                call(
                    " - Challenge file 'files/test-file.png' specified, but not found at /challenge/files/test-file.png"
                ),
                call(),
            ]
        )
