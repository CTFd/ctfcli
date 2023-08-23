import configparser
import json
import os
from pathlib import Path

import appdirs

from ctfcli import __name__ as pkg_name
from ctfcli.core.exceptions import ProjectNotInitialized


class Config:
    def __init__(self):
        self.base_path = self.get_base_path()
        self.project_path = self.get_project_path()
        self.config_path = self.project_path / ".ctf" / "config"
        self.data_path = self.get_data_path()
        self.templates_path = self.get_templates_path()
        self.pages_path = self.get_pages_path()
        self.plugins_path = self.get_plugins_path()

        parser = configparser.ConfigParser()
        parser.optionxform = str
        parser.read(self.config_path)

        self.config = parser
        self.challenges = dict(self.config["challenges"])

    def __getitem__(self, key):
        return self.config[key]

    def __contains__(self, key):
        return key in self.config

    def write(self, file_handle):
        return self.config.write(file_handle)

    def as_json(self, pretty=False) -> str:
        data = {}
        for section in self.config.sections():
            data[section] = {}
            for k, v in self.config.items(section):
                data[section][k] = v

        if pretty:
            return json.dumps(data, sort_keys=True, indent=4)

        return json.dumps(data)

    @staticmethod
    def get_project_path() -> Path:
        pwd = Path.cwd()
        while pwd != Path("/"):
            config = pwd / ".ctf" / "config"
            if config.is_file():
                return pwd
            pwd = pwd.parent

        raise ProjectNotInitialized

    @staticmethod
    def get_config_path() -> Path:
        return Config.get_project_path() / ".ctf" / "config"

    @staticmethod
    def get_base_path() -> Path:
        return Path(__file__).parent.parent

    @staticmethod
    def get_data_path() -> Path:
        return Path(appdirs.user_data_dir(appname=pkg_name))

    @staticmethod
    def get_pages_path() -> Path:
        pages_path = Config.get_project_path() / "pages"

        if not pages_path.exists():
            pages_path.mkdir()

        return pages_path

    @staticmethod
    def get_templates_path() -> Path:
        templates_path = Config.get_data_path() / "templates"

        if not templates_path.exists():
            templates_path.mkdir(parents=True)

        return templates_path

    @staticmethod
    def get_plugins_path() -> Path:
        if os.getenv("CTFCLI_PLUGIN_PATH"):
            plugins_path = Config._get_custom_plugin_path()
        else:
            plugins_path = Config.get_data_path() / "plugins"

        if not plugins_path.exists():
            plugins_path.mkdir(parents=True)

        return plugins_path

    @staticmethod
    def _get_custom_plugin_path() -> Path:
        # Assumes CTFCLI_PLUGIN_PATH is present
        custom_plugins_path = Path(os.getenv("CTFCLI_PLUGIN_PATH"))

        if custom_plugins_path.is_absolute():
            return custom_plugins_path

        # If path is relative, assume it's to ctfcli base_path (development convenience)
        return Config.get_base_path() / custom_plugins_path
