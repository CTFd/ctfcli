import os
import shutil
import subprocess

import click

from ctfcli.utils.plugins import get_plugin_dir


class Plugins(object):
    def install(self, url):
        local_dir = os.path.join(
            get_plugin_dir(), os.path.basename(url).rsplit(".", maxsplit=1)[0]
        )
        subprocess.call(["git", "clone", url, local_dir])

        pip = shutil.which("pip")
        pip3 = shutil.which("pip3")

        if pip is None and pip3 is None:
            click.secho("Neither pip nor pip3 was found, is it in the PATH?", fg="red")
            return

        if pip is None:
            pip = pip3

        subprocess.call(
            [pip, "install", "-r", os.path.join(local_dir, "requirements.txt")]
        )

    def uninstall(self, plugin_name):
        plugin_dir = os.path.join(get_plugin_dir(), plugin_name)
        shutil.rmtree(plugin_dir)

    def list(self):
        for plugin in sorted(os.listdir(get_plugin_dir())):
            print(plugin)

    def dir(self):
        print(get_plugin_dir())
