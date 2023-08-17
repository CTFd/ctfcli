import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock

from ctfcli.core.config import Config
from ctfcli.core.exceptions import ProjectNotInitialized

BASE_DIR = Path(__file__).parent.parent


class TestConfig(unittest.TestCase):
    minimal_challenge_cwd = BASE_DIR / "fixtures" / "challenges" / "test-challenge-minimal"

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=Path(tempfile.mkdtemp()))
    def test_raises_if_config_is_not_found(self, *args, **kwargs):
        with self.assertRaises(ProjectNotInitialized):
            Config()

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    def test_determines_project_path(self, *args, **kwargs):
        config = Config()
        expected_project_path = BASE_DIR / "fixtures" / "challenges"
        self.assertEqual(expected_project_path, config.project_path)
        self.assertEqual(expected_project_path, config.get_project_path())

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    def test_determines_base_path(self, *args, **kwargs):
        config = Config()
        expected_base_path = BASE_DIR.parent / "ctfcli"
        self.assertEqual(expected_base_path, config.base_path)
        self.assertEqual(expected_base_path, config.get_base_path())

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    def test_determines_config_path(self, *args, **kwargs):
        config = Config()
        expected_config_path = BASE_DIR / "fixtures" / "challenges" / ".ctf" / "config"
        self.assertEqual(expected_config_path, config.config_path)
        self.assertEqual(expected_config_path, config.get_config_path())

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.config.configparser.ConfigParser")
    def test_reads_config(self, mock_configparser: MagicMock, *args, **kwargs):
        Config()
        expected_config_path = BASE_DIR / "fixtures" / "challenges" / ".ctf" / "config"
        mock_configparser.return_value.read.assert_called_once_with(expected_config_path)

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.config.configparser.ConfigParser")
    def test_writes_config(self, mock_configparser: MagicMock, *args, **kwargs):
        config = Config()

        with tempfile.NamedTemporaryFile(delete=True) as tmp_config:
            config.write(tmp_config)
            mock_configparser.return_value.write.assert_called_once_with(tmp_config)

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    def test_returns_correct_json_representation(self, *args, **kwargs):
        config = Config()

        expected_config = {
            "config": {"access_token": "deadbeef", "url": "https://example.com/"},
            "challenges": {
                "test-challenge-dockerfile": "user@host:example/test-challenge-dockerfile.git",
                "test-challenge-files": "user@host:example/test-challenge-files.git",
                "test-challenge-full": "user@host:example/test-challenge-full.git",
                "test-challenge-minimal": "user@host:example/test-challenge-minimal.git",
            },
        }

        config_data = json.loads(config.as_json())
        self.assertEqual(expected_config, config_data)

        config_data_pretty = json.loads(config.as_json(pretty=True))
        self.assertEqual(expected_config, config_data_pretty)

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    def test_overloads_getitem(self, *args, **kwargs):
        config = Config()

        # test that config can be directly accessed like a dictionary
        self.assertEqual(config["config"]["url"], "https://example.com/")
        self.assertEqual(
            config["challenges"]["test-challenge-minimal"],
            "user@host:example/test-challenge-minimal.git",
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    def test_overloads_contains(self, *args, **kwargs):
        config = Config()
        # test that config can be queried with 'in'
        self.assertTrue("challenges" in config)

    def test_get_data_path_returns_path(self):
        data_path = Config.get_data_path()
        self.assertIsInstance(data_path, Path)

    def test_get_templates_path_returns_path(self):
        templates_path = Config.get_templates_path()
        self.assertIsInstance(templates_path, Path)

    @mock.patch("ctfcli.core.config.appdirs.user_data_dir")
    def test_get_data_path_calls_appdirs(self, mock_user_data_path: MagicMock):
        Config.get_data_path()
        mock_user_data_path.assert_called_once_with(appname="ctfcli")

    @mock.patch(
        "ctfcli.core.config.Config.get_data_path",
        return_value=Path("/tmp/test/ctfcli-data"),
    )
    @mock.patch.object(Path, "mkdir")
    @mock.patch.object(Path, "exists")
    def test_get_templates_path(self, mock_exists: MagicMock, mock_mkdir: MagicMock, *args, **kwargs):
        expected_templates_path = Path("/tmp/test/ctfcli-data/templates")
        mock_exists.return_value = False

        templates_path = Config.get_templates_path()

        self.assertEqual(templates_path, expected_templates_path)
        mock_mkdir.assert_called_once()

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    def test_get_pages_path_returns_path(self, *args, **kwargs):
        pages_path = Config.get_pages_path()
        self.assertIsInstance(pages_path, Path)

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    def test_get_pages_path(self, *args, **kwargs):
        expected_pages_path = BASE_DIR / "fixtures" / "challenges" / "pages"
        pages_path = Config.get_pages_path()
        self.assertEqual(expected_pages_path, pages_path)

    @mock.patch(
        "ctfcli.core.config.Config.get_project_path",
        return_value=Path("/tmp/test/ctfcli-project"),
    )
    @mock.patch.object(Path, "mkdir")
    @mock.patch.object(Path, "exists")
    def test_get_pages_path_creates_directory(self, mock_exists: MagicMock, mock_mkdir: MagicMock, *args, **kwargs):
        expected_pages_path = Path("/tmp/test/ctfcli-project/pages")
        mock_exists.return_value = False

        pages_path = Config.get_pages_path()

        self.assertEqual(pages_path, expected_pages_path)
        mock_mkdir.assert_called_once()

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch(
        "ctfcli.core.config.Config.get_data_path",
        return_value=Path("/tmp/test/ctfcli-data"),
    )
    def test_get_plugins_path(self, *args, **kwargs):
        expected_plugins_path = Path("/tmp/test/ctfcli-data") / "plugins"
        pages_path = Config.get_plugins_path()
        self.assertEqual(expected_plugins_path, pages_path)

    @mock.patch(
        "ctfcli.core.config.Config.get_data_path",
        return_value=Path("/tmp/test/ctfcli-data"),
    )
    @mock.patch.object(Path, "mkdir")
    @mock.patch.object(Path, "exists")
    def test_get_plugins_path_creates_directory(self, mock_exists: MagicMock, mock_mkdir: MagicMock, *args, **kwargs):
        expected_plugins_path = Path("/tmp/test/ctfcli-data/plugins")
        mock_exists.return_value = False

        plugins_path = Config.get_plugins_path()

        self.assertEqual(expected_plugins_path, plugins_path)
        mock_mkdir.assert_called_once()

    @mock.patch.dict(os.environ, {"CTFCLI_PLUGIN_PATH": "/tmp/test/custom-plugins-directory"})
    @mock.patch.object(Path, "exists")
    def test_get_plugins_path_uses_overriden_directory(self, mock_exists: MagicMock, *args, **kwargs):
        expected_plugins_path = Path("/tmp/test/custom-plugins-directory")
        mock_exists.return_value = True

        plugins_path = Config.get_plugins_path()
        self.assertEqual(expected_plugins_path, plugins_path)

    @mock.patch.dict(os.environ, {"CTFCLI_PLUGIN_PATH": "custom-plugins-directory"})
    @mock.patch.object(Path, "exists")
    def test_get_plugins_path_accepts_relative_directory_override(self, mock_exists: MagicMock, *args, **kwargs):
        expected_plugins_path = BASE_DIR.parent / "ctfcli" / "custom-plugins-directory"
        mock_exists.return_value = True

        plugins_path = Config.get_plugins_path()

        self.assertEqual(expected_plugins_path, plugins_path)
