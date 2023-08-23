import unittest
from unittest import mock

from ctfcli.utils.tools import strings


class TestStrings(unittest.TestCase):
    @mock.patch("builtins.open", mock.mock_open(read_data="Hello\x02World\x88!"))
    def test_returns_printable(self):
        result = strings("/tmp/test/ctfcli/doesnotmatter.bin")
        self.assertEqual(["Hello", "World"], list(result))

    @mock.patch("builtins.open", mock.mock_open(read_data="Hello\x02Wor\x02ld\x88!"))
    def test_does_not_catch_results_shorter_than_min_length(self):
        result = strings("/tmp/test/ctfcli/doesnotmatter.bin", min_length=10)
        self.assertEqual([], list(result))

        result = strings("/tmp/test/ctfcli/doesnotmatter.bin")
        self.assertEqual(["Hello"], list(result))

        result = strings("/tmp/test/ctfcli/doesnotmatter.bin", min_length=2)
        self.assertEqual(["Hello", "Wor", "ld"], list(result))

    @mock.patch("builtins.open", mock.mock_open(read_data="\x88\x02\x02\x88"))
    def test_returns_empty_generator_if_no_strings_found(self):
        result = strings("/tmp/test/ctfcli/doesnotmatter.bin")
        self.assertEqual([], list(result))
