import logging
import subprocess
import time
from typing import Dict, Optional
from urllib.parse import urlparse

import click

from ctfcli.core.api import API
from ctfcli.core.config import Config
from ctfcli.core.deployment.base import DeploymentHandler, DeploymentResult

log = logging.getLogger("ctfcli.core.deployment.cloud")


class CloudDeploymentHandler(DeploymentHandler):
    def __init__(self, *args, **kwargs):
        super(CloudDeploymentHandler, self).__init__(*args, **kwargs)

        self.api = API()
        self.config = Config()

        # Do not fail here if challenge does not provide an image
        # rather return a failed deployment result during deploy
        if self.challenge.get("image"):
            self.image_name = self.challenge.image.name

    def deploy(self, skip_login=False, *args, **kwargs) -> DeploymentResult:
        # Check whether challenge defines image
        if not self.challenge.get("image"):
            click.secho("Challenge does not define an image to deploy", fg="red")
            return DeploymentResult(False)

        # Check whether instance supports cloud deployments
        check = self.api.get("/api/v1/images")
        if not check.ok:
            click.secho("Target instance does not support cloud deployments", fg="red")
            return DeploymentResult(False)

        # Get or create Image in CTFd
        image_data = self._get_or_create_image()

        # Build new / initial version of the image
        image_name = self.challenge.image.build()
        if not image_name:
            click.secho("Could not build the image. Please check docker output above.", fg="red")
            return DeploymentResult(False)

        if skip_login:
            click.secho(
                "Skipping registry login because of --skip-login. Make sure you are logged in to the registry.",
                fg="yellow",
            )
        else:
            login_result = self._registry_login()

            if not login_result:
                click.secho(
                    "Could not log in to the registry. Please check your access token and instance URL", fg="red"
                )
                return DeploymentResult(False)

        push_result = self.challenge.image.push(image_data["location"])
        if not push_result:
            click.secho("Could not push image to the registry.", fg="red")

            if skip_login:
                click.secho(
                    "Remember that you need to manually login to the docker registry when using --skip-login",
                    fg="yellow",
                )

            return DeploymentResult(False)

        # Get or create Service in CTFd
        service_data = self._get_or_create_service(image_data["location"])

        deployed_service_data = self._await_service_deployment(service_data)
        if not deployed_service_data:
            return DeploymentResult(False)

        # Expose TCP port if configured
        if self.protocol == "tcp":
            self.api.patch(f"/api/v1/services/{deployed_service_data['id']}", json={"expose": True}).raise_for_status()
            deployed_service_data = self.api.get(f"/api/v1/services/{deployed_service_data['id']}").json()["data"]

        connection_info = self._get_connection_info(
            hostname=deployed_service_data["hostname"],
            tcp_hostname=deployed_service_data.get("tcp_hostname"),
            tcp_port=deployed_service_data.get("tcp_port"),
        )

        return DeploymentResult(True, connection_info=connection_info)

    def _get_or_create_image(self):
        # Check if image already exists
        existing_images = self.api.get("/api/v1/images").json()["data"]
        for image_data in existing_images:
            if image_data["location"].endswith(self.image_name):
                return image_data

        # Create the image if it doesn't exist
        return self.api.post("/api/v1/images", json={"name": self.image_name}).json()["data"]

    def _get_or_create_service(self, image_location: str):
        existing_services = self.api.get("/api/v1/services").json()["data"]
        for service_data in existing_services:
            if service_data["name"] == self.image_name:
                # Update the existing service image information
                self.api.patch(
                    f"/api/v1/services/{service_data['id']}",
                    json={"image": image_location},
                ).raise_for_status()
                return self.api.get(f"/api/v1/services/{service_data['id']}").json()["data"]

        # Create the service if it doesn't exist
        return self.api.post("/api/v1/services", json={"name": self.image_name, "image": image_location}).json()["data"]

    def _await_service_deployment(self, service_data, interval=10, timeout=180) -> Optional[Dict]:
        service_id = service_data["id"]

        base_timeout = timeout
        i = 0
        while service_data.get("hostname") is None and timeout > 0:
            click.secho(
                f"Awaiting service deployment [{i * interval}/{base_timeout}s]",
                fg="yellow",
            )
            service_data = self.api.get(f"/api/v1/services/{service_id}").json()["data"]

            i += 1
            timeout -= interval
            time.sleep(interval)

        if timeout == 0:
            click.secho("Timeout awaiting challenge deployment", fg="red")
            return

        return service_data

    def _registry_login(self, registry: str = "registry.ctfd.io") -> bool:
        r = self.api.get("/api/v1/users/me")
        r.raise_for_status()
        data = r.json()

        if not data["success"]:
            return False

        # build registry username: admin@instance.ctfd.io
        username = data["data"]["name"]
        hostname = urlparse(self.api.prefix_url).hostname

        # require instance url to be ctfd assigned for now
        # later this could use dig to resolve a cname record
        if not hostname or not str(hostname).endswith(".ctfd.io"):
            click.secho(
                "Instance URL is not a CTFd assigned URL. Either use the CTFd assigned domain name, "
                "or login to the registry manually and deploy with --skip-login",
                fg="red",
            )
            return False

        docker_login = f"{username}@{hostname}"
        docker_password = self.api.access_token.encode()
        docker_login_command = [
            "docker",
            "login",
            "-u",
            docker_login,
            "--password-stdin",
            registry,
        ]

        log.debug(f"call({docker_login_command}, stderr=subprocess.PIPE, input=docker_password)")
        login_response = subprocess.check_output(docker_login_command, input=docker_password, stderr=subprocess.PIPE)

        if b"Login Succeeded" in login_response:
            return True

        return False

    def _get_connection_info(
        self,
        hostname: str,
        tcp_hostname: Optional[str] = None,
        tcp_port: Optional[str] = None,
    ) -> str:
        # if protocol is http(s) - return an URL
        if self.protocol and self.protocol.startswith("http"):
            # cloud deployments always deploy on https
            return f"https://{hostname}"

        # if protocol is tcp, and connection details are provided - return netcat connection string
        if self.protocol and self.protocol == "tcp" and tcp_hostname and tcp_port:
            return f"nc {tcp_hostname} {tcp_port}"

        # Otherwise return plain hostname
        return hostname
