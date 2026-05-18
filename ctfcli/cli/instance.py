import logging

import click

from ctfcli.core.config import Config
from ctfcli.core.instance.config import ServerConfig

log = logging.getLogger("ctfcli.cli.instance")


class ConfigCommand:
    def get(self, key):
        """Get the value of a specific remote instance config key"""
        log.debug(f"ConfigCommand.get: ({key=})")
        return ServerConfig.get(key=key)

    def set(self, key, value):
        """Set the value of a specific remote instance config key"""
        log.debug(f"ConfigCommand.set: ({key=})")
        ServerConfig.set(key=key, value=value)
        click.secho(f"Successfully set '{key}' to '{value}'", fg="green")

    def pull(self):
        """Copy remote instance configuration values to local config"""
        log.debug("ConfigCommand.pull")
        server_configs = ServerConfig.getall()

        config = Config()
        if config.config.has_section("instance") is False:
            config.config.add_section("instance")

        for k, v in server_configs.items():
            # We always store as a string because the CTFd Configs model is a string
            if v == "None":
                v = "null"
            config.config.set("instance", k, str(v))

        with open(config.config_path, "w+") as f:
            config.write(f)

        click.secho("Successfully pulled configuration", fg="green")

    def push(self):
        """Save local instance configuration values to remote CTFd instance"""
        log.debug("ConfigCommand.push")
        config = Config()
        if config.config.has_section("instance") is False:
            config.config.add_section("instance")

        configs = {}
        for k in config["instance"]:
            v = config["instance"][k]
            if v == "null":
                v = None
            configs[k] = v

        failed_configs = ServerConfig.setall(configs=configs)
        for f in failed_configs:
            click.secho(f"Failed to push config {f}", fg="red")

        if not failed_configs:
            click.secho("Successfully pushed config", fg="green")
            return 0

        return 1


class InstanceCommand:
    def config(self):
        return ConfigCommand
