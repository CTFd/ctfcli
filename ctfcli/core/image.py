import json
import subprocess
import tempfile
from os import PathLike
from pathlib import Path
from typing import Optional, Union


class Image:
    def __init__(self, name: str, build_path: Optional[Union[str, PathLike]] = None):
        # name can be either a new name to assign or an existing image name
        self.name = name

        # if the image is a remote image (eg. ghcr.io/.../...), extract the basename
        self.basename = name
        if "/" in self.name or "" in self.name:
            self.basename = self.name.split(":")[0].split("/")[-1]

        self.built = True

        # if the image provides a build path, assume it is not built yet
        if build_path:
            self.build_path = Path(build_path)
            self.built = False

    def build(self) -> Optional[str]:
        docker_build = subprocess.call(["docker", "build", "-t", self.name, "."], cwd=self.build_path.absolute())
        if docker_build != 0:
            return

        self.built = True
        return self.name

    def pull(self) -> Optional[str]:
        docker_pull = subprocess.call(["docker", "pull", self.name])
        if docker_pull != 0:
            return

        return self.name

    def push(self, location: str) -> Optional[str]:
        if not self.built:
            self.build()

        docker_tag = subprocess.call(["docker", "tag", self.name, location])
        docker_push = subprocess.call(["docker", "push", location])

        if any(r != 0 for r in [docker_tag, docker_push]):
            return

        return location

    def export(self) -> Optional[str]:
        if not self.built:
            self.build()

        image_tar = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{self.basename}.docker.tar")
        docker_save = subprocess.call(["docker", "save", "--output", image_tar.name, self.name])

        if docker_save != 0:
            return

        return image_tar.name

    def get_exposed_port(self) -> Optional[str]:
        if not self.built:
            self.build()

        try:
            docker_output = subprocess.check_output(
                ["docker", "inspect", "--format={{json .Config.ExposedPorts}}", self.name]
            )
        except subprocess.CalledProcessError:
            return

        ports_data = json.loads(docker_output)
        if ports_data:
            ports = list(ports_data.keys())

            if ports:
                # Split '2323/tcp'
                return ports[0].split("/")[0]
