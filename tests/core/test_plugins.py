import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, call

from ctfcli.core.config import Config
from ctfcli.core.plugins import load_plugins


class TestPlugins(unittest.TestCase):
    @mock.patch.object(Config, "get_plugins_path")
    @mock.patch("ctfcli.core.plugins.importlib.import_module")
    def test_load_plugins(self, mock_import: MagicMock, mock_plugins_path: MagicMock):
        mock_plugins_path.return_value = MagicMock()
        mock_plugins_path.return_value.absolute.return_value = Path("/tmp/test")
        mock_plugins_path.return_value.iterdir.return_value = [Path("/tmp/test/test_plugin")]

        test_commands = {"challenge": None, "pages": None}
        load_plugins(test_commands)

        mock_import.assert_has_calls([call("test_plugin")])
        mock_import.return_value.load.assert_called_once_with(test_commands)
