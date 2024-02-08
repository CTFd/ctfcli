import unittest
from pathlib import Path
from subprocess import CalledProcessError
from unittest import mock
from unittest.mock import MagicMock, call

from ctfcli.core.challenge import Challenge
from ctfcli.core.deployment import SSHDeploymentHandler
from ctfcli.core.deployment.base import DeploymentResult

BASE_DIR = Path(__file__).parent.parent.parent


class TestSSHDeployment(unittest.TestCase):
    challenge_directory = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
    challenge_path = challenge_directory / "challenge.yml"

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch.object(Path, "unlink")
    @mock.patch("ctfcli.core.deployment.ssh.subprocess.run")
    @mock.patch("ctfcli.core.deployment.ssh.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    def test_builds_exports_and_copies_image(
        self,
        mock_image_constructor: MagicMock,
        mock_secho: MagicMock,
        mock_subprocess: MagicMock,
        mock_unlink: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.basename = "test-challenge"
        mock_image.build.return_value = "test-challenge"
        mock_image.export.return_value = "/tmp/test/test-challenge.tar"
        mock_image.get_exposed_port.return_value = 80

        handler = SSHDeploymentHandler(challenge, host="ssh://root@127.0.0.1")
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertTrue(result.success)
        self.assertEqual("http://127.0.0.1", result.connection_info)

        mock_secho.assert_not_called()
        mock_subprocess.assert_has_calls(
            [
                call(["scp", Path("/tmp/test/test-challenge.tar"), "root@127.0.0.1:/tmp/test-challenge.tar"]),
                call(["ssh", "root@127.0.0.1", "docker load -i /tmp/test-challenge.tar && rm /tmp/test-challenge.tar"]),
                call(
                    [
                        "ssh",
                        "root@127.0.0.1",
                        "docker stop test-challenge 2>/dev/null; docker rm test-challenge 2>/dev/null",
                    ]
                ),
                call(
                    [
                        "ssh",
                        "root@127.0.0.1",
                        "docker run -d -p80:80 --name test-challenge --restart always test-challenge",
                    ]
                ),
            ]
        )

        mock_unlink.assert_called_once()

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.ssh.click.secho")
    def test_fails_deployment_if_challenge_does_not_provide_image(self, mock_secho: MagicMock, *args, **kwargs):
        challenge = Challenge(self.challenge_path, {"image": None, "host": "ssh://root@127.0.0.1"})
        handler = SSHDeploymentHandler(challenge)
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_called_once_with("Challenge does not define an image to deploy", fg="red")

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.ssh.click.secho")
    def test_fails_deployment_if_no_host_provided(self, mock_secho: MagicMock, *args, **kwargs):
        challenge = Challenge(self.challenge_path)
        handler = SSHDeploymentHandler(challenge)
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_called_once_with(
            "No host provided for the deployment. Use --host, or define host in the challenge.yml file", fg="red"
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.ssh.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    def test_fails_deployment_if_image_build_failed(
        self,
        mock_image_constructor: MagicMock,
        mock_secho: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)
        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.built = False
        mock_image.build.return_value = None

        handler = SSHDeploymentHandler(challenge, host="ssh://root@127.0.0.1")
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_called_once_with("Could not build the image. Please check docker output above.", fg="red")

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.ssh.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    def test_fails_deployment_if_image_export_failed(
        self,
        mock_image_constructor: MagicMock,
        mock_secho: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.basename = "test-challenge"
        mock_image.build.return_value = "test-challenge"
        mock_image.export.return_value = None

        handler = SSHDeploymentHandler(challenge, host="ssh://root@127.0.0.1")
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_called_once_with("Could not export the image. Please check docker output above.", fg="red")

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.ssh.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    def test_fails_deployment_if_no_exposed_port(
        self,
        mock_image_constructor: MagicMock,
        mock_secho: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.basename = "test-challenge"
        mock_image.build.return_value = "test-challenge"
        mock_image.export.return_value = "/tmp/test/test-challenge.tar"
        mock_image.get_exposed_port.return_value = None

        handler = SSHDeploymentHandler(challenge, host="ssh://root@127.0.0.1")
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_called_once_with(
            "Could not resolve a port to expose. Make sure your Dockerfile EXPOSE's a port.", fg="red"
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.ssh.subprocess.run")
    @mock.patch("ctfcli.core.deployment.ssh.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    def test_fails_deployment_if_any_subprocess_exits(
        self,
        mock_image_constructor: MagicMock,
        mock_secho: MagicMock,
        mock_subprocess: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.basename = "test-challenge"
        mock_image.build.return_value = "test-challenge"
        mock_image.export.return_value = "/tmp/test/test-challenge.tar"
        mock_image.get_exposed_port.return_value = 80

        mock_subprocess.side_effect = [CalledProcessError(1, "test-exception")]

        handler = SSHDeploymentHandler(challenge, host="ssh://root@127.0.0.1")
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_has_calls(
            [
                call("Failed to deploy image!", fg="red"),
                call("Command 'test-exception' returned non-zero exit status 1.", fg="red"),
            ]
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    def test_get_connection_info_http_s(self, *args, **kwargs):
        challenge = Challenge(self.challenge_path)

        handler = SSHDeploymentHandler(challenge, host="ssh://root@127.0.0.1", protocol="http")
        connection_info_http = handler._get_connection_info("127.0.0.1", 8080)
        self.assertEqual("http://127.0.0.1:8080", connection_info_http)

        handler = SSHDeploymentHandler(challenge, host="ssh://root@127.0.0.1", protocol="https")
        connection_info_https = handler._get_connection_info("127.0.0.1", 8443)
        self.assertEqual("https://127.0.0.1:8443", connection_info_https)

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    def test_get_connection_info_does_not_assign_standard_ports(self, *args, **kwargs):
        challenge = Challenge(self.challenge_path)

        handler = SSHDeploymentHandler(challenge, host="ssh://root@127.0.0.1", protocol="http")
        connection_info_http = handler._get_connection_info("127.0.0.1", 80)
        self.assertEqual("http://127.0.0.1", connection_info_http)

        handler = SSHDeploymentHandler(challenge, host="ssh://root@127.0.0.1", protocol="https")
        connection_info_https = handler._get_connection_info("127.0.0.1", 443)
        self.assertEqual("https://127.0.0.1", connection_info_https)

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    def test_get_connection_info_tcp(self, *args, **kwargs):
        challenge = Challenge(self.challenge_path)

        handler = SSHDeploymentHandler(challenge, host="ssh://root@127.0.0.1", protocol="tcp")
        connection_info = handler._get_connection_info("127.0.0.1", 9001)
        self.assertEqual("nc 127.0.0.1 9001", connection_info)

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    def test_get_connection_info_fallback(self, *args, **kwargs):
        challenge = Challenge(self.challenge_path, {"protocol": None})

        handler = SSHDeploymentHandler(challenge, host="ssh://root@127.0.0.1")
        connection_info = handler._get_connection_info("127.0.0.1", 9001)
        self.assertEqual("127.0.0.1", connection_info)
