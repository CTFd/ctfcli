import logging
import shutil
import subprocess
from glob import glob
from pathlib import Path

import click

from ctfcli.core.config import Config

log = logging.getLogger("ctfcli.cli.templates")


class TemplatesCommand:
    @staticmethod
    def install(template_url: str) -> int:
        log.debug(f"install: {template_url}")

        templates_path = Config.get_templates_path()
        if not template_url.endswith(".git"):
            click.secho(
                "Can only install templates from git repositories - " f"{template_url} does not end with .git",
                fg="red",
            )
            return 1

        installed_template_path = templates_path / Path(template_url).stem
        git_clone = subprocess.call(["git", "clone", template_url, installed_template_path])

        if git_clone != 0:
            click.secho(
                "Failed to clone the template repository. Please check git output above.",
                fg="red",
            )
            return 1

        return 0

    @staticmethod
    def uninstall(template_name: str) -> int:
        log.debug(f"uninstall: {template_name}")

        templates_path = Config.get_templates_path()
        template_path = templates_path / template_name

        if not template_path.exists():
            click.secho(f"Could not find template {template_name} in {templates_path}", fg="red")
            return 1

        shutil.rmtree(template_path)
        return 0

    @staticmethod
    def list() -> int:
        log.debug("list")

        base_path = Config.get_base_path()
        templates_path = Config.get_templates_path()

        # Echo built-in templates
        built_in_templates = base_path / "templates"

        click.secho("List of built-in templates:", fg="blue")
        for template in built_in_templates.iterdir():
            click.echo(f" - {template.relative_to(built_in_templates)}")

        # echo a new line separator
        click.echo()

        installed_templates = glob(f"{templates_path}/**/*/cookiecutter.json", recursive=True)
        if len(installed_templates) == 0:
            click.secho("Found no user-installed templates", fg="blue")
            return 0

        click.secho("List of user-installed templates:", fg="blue")
        for template in installed_templates:
            # Remove prefix of templates_path (+1 for last slash) and remove suffix of /cookiecutter.json
            template_path = str(template)[len(str(templates_path)) + 1 : -len("/cookiecutter.json")]
            click.echo(f" - {template_path}")

        return 0

    @staticmethod
    def dir() -> int:
        log.debug("dir")
        return TemplatesCommand.path()

    @staticmethod
    def path() -> int:
        log.debug("path")
        click.echo(Config.get_templates_path())
        return 0
