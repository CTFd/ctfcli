import os
import shutil
import subprocess
from glob import glob

from ctfcli.utils.templates import get_template_dir


class Templates(object):
    def install(self, url):
        local_dir = os.path.join(
            get_template_dir(), os.path.basename(url).rsplit(".", maxsplit=1)[0]
        )
        subprocess.call(["git", "clone", url, local_dir])

    def uninstall(self, template_name):
        template_dir = os.path.join(get_template_dir(), template_name)
        shutil.rmtree(template_dir)

    def list(self):
        template_dir = get_template_dir() + "/"
        for template in glob(f"{template_dir}/**/*/cookiecutter.json"):
            # Remove prefix of template_dir and remove suffix of /cookiecutter.json
            template = template[len(template_dir) : -len("/cookiecutter.json")]
            print(template)

    def dir(self):
        print(get_template_dir())
