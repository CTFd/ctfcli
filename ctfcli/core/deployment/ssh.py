import subprocess
from pathlib import Path
from urllib.parse import urlparse

import click

from ctfcli.core.deployment.base import DeploymentHandler, DeploymentResult


class SSHDeploymentHandler(DeploymentHandler):
    def deploy(self, *args, **kwargs) -> DeploymentResult:
        if not self.challenge.get("image"):
            click.secho("Challenge does not define an image to deploy", fg="red")
            return DeploymentResult(False)

        if not self.host:
            click.secho(
                "No host provided for the deployment. Use --host, or define host in the challenge.yml file", fg="red"
            )
            return DeploymentResult(False)

        build_result = self.challenge.image.build()
        if not build_result:
            click.secho("Could not build the image. Please check docker output above.", fg="red")
            return DeploymentResult(False)

        image_name = self.challenge.image.name
        export_result = self.challenge.image.export()
        if not export_result:
            click.secho("Could not export the image. Please check docker output above.", fg="red")
            return DeploymentResult(False)

        image_export_path = Path(export_result)
        host_url = urlparse(self.host)
        target_path = host_url.path or "/tmp"
        target_file = f"{target_path}/{image_export_path.name}"

        exposed_port = self.challenge.image.get_exposed_port()
        if not exposed_port:
            click.secho("Could not resolve a port to expose. Make sure your Dockerfile EXPOSE's a port.", fg="red")
            return DeploymentResult(False)

        target_hostname = host_url.netloc[host_url.netloc.find("@") + 1 :]
        try:
            subprocess.run(["scp", image_export_path, f"{host_url.netloc}:{target_file}"])
            subprocess.run(
                [
                    "ssh",
                    host_url.netloc,
                    f"docker load -i {target_file} && rm {target_file}",
                ]
            )
            subprocess.run(
                [
                    "ssh",
                    host_url.netloc,
                    f"docker stop {image_name} 2>/dev/null; docker rm {image_name} 2>/dev/null",
                ]
            )
            subprocess.run(
                [
                    "ssh",
                    host_url.netloc,
                    f"docker run -d -p{exposed_port}:{exposed_port} --name {image_name} --restart always {image_name}",
                ]
            )

        except subprocess.CalledProcessError as e:
            click.secho("Failed to deploy image!", fg="red")
            click.secho(str(e), fg="red")
            return DeploymentResult(False)

        image_export_path.unlink()

        connection_info = self._get_connection_info(target_hostname, exposed_port)
        return DeploymentResult(True, target_hostname, exposed_port, connection_info)

    def _get_connection_info(self, hostname: str, port: int) -> str:
        # if protocol is http(s) - return an URL
        if self.protocol and self.protocol.startswith("http"):
            # if port is the default for http or https don't include a port
            if port == 80 and self.protocol == "http":
                return f"http://{hostname}"

            if port == 443 and self.protocol == "https":
                return f"https://{hostname}"

            return f"{self.protocol}://{hostname}:{port}"

        # if protocol is tcp, and connection details are provided - return netcat connection string
        if self.protocol and self.protocol == "tcp":
            return f"nc {hostname} {port}"

        # Otherwise return plain hostname
        return hostname
