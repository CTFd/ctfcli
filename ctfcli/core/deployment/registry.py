import logging
import subprocess
from urllib.parse import urlparse

import click

from ctfcli.core.config import Config
from ctfcli.core.deployment.base import DeploymentHandler, DeploymentResult

log = logging.getLogger("ctfcli.core.deployment.registry")


class RegistryDeploymentHandler(DeploymentHandler):
    def deploy(self, skip_login=False, *args, **kwargs) -> DeploymentResult:
        config = Config()

        # Check whether challenge defines image
        if not self.challenge.get("image"):
            click.secho("Challenge does not define an image to deploy", fg="red")
            return DeploymentResult(False)

        if not self.host:
            click.secho(
                "No host provided for the deployment. Use --host, or define host in the challenge.yml file", fg="red"
            )
            return DeploymentResult(False)

        # resolve a location for the image push
        # e.g. registry.example.com/test-project/challenge-image-name
        # challenge image name is appended to the host provided for the deployment
        host_url = urlparse(self.host)
        location = f"{host_url.netloc}{host_url.path.rstrip('/')}/{self.challenge.image.name}"

        if skip_login:
            click.secho(
                "Skipping registry login because of --skip-login. Make sure you are logged in to the registry.",
                fg="yellow",
            )
        else:
            if "registry" not in config or not config["registry"]:
                click.secho("Config does not provide a registry section.", fg="red")
                return DeploymentResult(False)

            registry_username = config["registry"].get("username")
            registry_password = config["registry"].get("password")
            if not registry_username or not registry_password:
                click.secho("Config is missing credentials for the registry.", fg="red")
                return DeploymentResult(False)

            login_result = self._registry_login(
                registry_username,
                registry_password,
                host_url.netloc,
            )

            if not login_result:
                click.secho("Could not log in to the registry. Please check your configured credentials.", fg="red")
                return DeploymentResult(False)

        build_result = self.challenge.image.build()
        if not build_result:
            click.secho("Could not build the image. Please check docker output above.", fg="red")
            return DeploymentResult(False)

        push_result = self.challenge.image.push(location)
        if not push_result:
            click.secho("Could not push image to the registry. Please check docker output above.", fg="red")

            if skip_login:
                click.secho(
                    "Remember that you need to manually login to the docker registry when using --skip-login",
                    fg="yellow",
                )

            return DeploymentResult(False)

        # In this deployment result we can't really provide more data such as the connection info, as we don't know
        # where and how the service is deployed - only that it's pushed to a registry
        return DeploymentResult(True)

    def _registry_login(self, username: str, password: str, registry: str):
        docker_login_command = [
            "docker",
            "login",
            "-u",
            username,
            "--password-stdin",
            registry,
        ]

        try:
            log.debug(f"call({docker_login_command}, stderr=subprocess.PIPE, input=password)")
            subprocess.run(
                docker_login_command, input=password.encode(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError:
            return False
        return True
