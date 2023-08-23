import unittest
from pathlib import Path
from subprocess import CalledProcessError
from unittest import mock
from unittest.mock import MagicMock, call

from ctfcli.core.challenge import Challenge
from ctfcli.core.deployment import RegistryDeploymentHandler
from ctfcli.core.deployment.base import DeploymentResult

BASE_DIR = Path(__file__).parent.parent.parent


class TestRegistryDeployment(unittest.TestCase):
    challenge_directory = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
    challenge_path = challenge_directory / "challenge.yml"

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.registry.subprocess.run")
    @mock.patch("ctfcli.core.deployment.registry.Config")
    @mock.patch("ctfcli.core.challenge.Image")
    def test_builds_and_pushes_image(
        self,
        mock_image_constructor: MagicMock,
        mock_config_constructor: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.build.return_value = "test-challenge"
        mock_image.push.return_value = "registry.example.com/example-project/test-challenge"

        mock_config_constructor.return_value = {"registry": {"username": "test", "password": "test"}}

        handler = RegistryDeploymentHandler(challenge, host="registry://registry.example.com/example-project")
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertTrue(result.success)

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.registry.click.secho")
    def test_fails_deployment_if_challenge_does_not_provide_image(self, mock_secho: MagicMock, *args, **kwargs):
        challenge = Challenge(self.challenge_path, {"image": None, "host": "registry.example.com/example-project"})
        handler = RegistryDeploymentHandler(challenge)
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_called_once_with("Challenge does not define an image to deploy", fg="red")

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.registry.click.secho")
    def test_fails_deployment_if_no_host_provided(self, mock_secho: MagicMock, *args, **kwargs):
        challenge = Challenge(self.challenge_path)
        handler = RegistryDeploymentHandler(challenge)
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_called_once_with(
            "No host provided for the deployment. Use --host, or define host in the challenge.yml file", fg="red"
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.registry.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    def test_fails_deployment_if_no_registry_config(
        self,
        mock_image_constructor: MagicMock,
        mock_secho: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.build.return_value = "test-challenge"

        handler = RegistryDeploymentHandler(challenge, host="registry://registry.example.com/example-project")
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_called_once_with("Config does not provide a registry section.", fg="red")

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.registry.click.secho")
    @mock.patch("ctfcli.core.deployment.registry.Config")
    @mock.patch("ctfcli.core.challenge.Image")
    def test_fails_if_no_credentials(
        self,
        mock_image_constructor: MagicMock,
        mock_config_constructor: MagicMock,
        mock_secho: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.build.return_value = "test-challenge"

        mock_config_constructor.return_value = {"registry": {"username": "test"}}

        handler = RegistryDeploymentHandler(challenge, host="registry://registry.example.com/example-project")
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_called_once_with("Config is missing credentials for the registry.", fg="red")

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.registry.click.secho")
    @mock.patch("ctfcli.core.deployment.registry.subprocess.run")
    @mock.patch("ctfcli.core.deployment.registry.Config")
    @mock.patch("ctfcli.core.challenge.Image")
    def test_fails_if_registry_credentials_invalid(
        self,
        mock_image_constructor: MagicMock,
        mock_config_constructor: MagicMock,
        mock_subprocess: MagicMock,
        mock_secho: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.build.return_value = "test-challenge"

        mock_config_constructor.return_value = {"registry": {"username": "test", "password": "test"}}
        mock_subprocess.side_effect = [CalledProcessError(1, "")]

        handler = RegistryDeploymentHandler(challenge, host="registry://registry.example.com/example-project")
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_called_once_with(
            "Could not log in to the registry. Please check your configured credentials.", fg="red"
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.registry.subprocess.run")
    @mock.patch("ctfcli.core.deployment.registry.click.secho")
    @mock.patch("ctfcli.core.deployment.registry.Config")
    @mock.patch("ctfcli.core.challenge.Image")
    def test_fails_deployment_if_image_build_failed(
        self,
        mock_image_constructor: MagicMock,
        mock_config_constructor: MagicMock,
        mock_secho: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.build.return_value = None

        mock_config_constructor.return_value = {"registry": {"username": "test", "password": "test"}}

        handler = RegistryDeploymentHandler(challenge, host="registry://registry.example.com/example-project")
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_called_once_with("Could not build the image. Please check docker output above.", fg="red")

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.registry.subprocess.run")
    @mock.patch("ctfcli.core.deployment.registry.click.secho")
    @mock.patch("ctfcli.core.deployment.registry.Config")
    @mock.patch("ctfcli.core.challenge.Image")
    def test_fails_deployment_if_image_push_failed(
        self,
        mock_image_constructor: MagicMock,
        mock_config_constructor: MagicMock,
        mock_secho: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.build.return_value = "test-challenge"
        mock_image.push.return_value = None

        mock_config_constructor.return_value = {"registry": {"username": "test", "password": "test"}}

        handler = RegistryDeploymentHandler(challenge, host="registry://registry.example.com/example-project")
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_called_once_with(
            "Could not push image to the registry. Please check docker output above.", fg="red"
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.registry.click.secho")
    @mock.patch("ctfcli.core.deployment.registry.subprocess.run")
    @mock.patch("ctfcli.core.deployment.registry.Config")
    @mock.patch("ctfcli.core.challenge.Image")
    def test_allows_skipping_login(
        self,
        mock_image_constructor: MagicMock,
        mock_config_constructor: MagicMock,
        mock_subprocess: MagicMock,
        mock_secho: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.build.return_value = "test-challenge"
        mock_image.push.return_value = "registry.example.com/example-project/test-challenge"

        mock_config_constructor.return_value = {"registry": {"username": "test", "password": "test"}}

        handler = RegistryDeploymentHandler(challenge, host="registry://registry.example.com/example-project")
        result = handler.deploy(skip_login=True)

        self.assertIsInstance(result, DeploymentResult)
        self.assertTrue(result.success)

        mock_secho.assert_called_once_with(
            "Skipping registry login because of --skip-login. Make sure you are logged in to the registry.",
            fg="yellow",
        )
        mock_subprocess.assert_not_called()

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.registry.click.secho")
    @mock.patch("ctfcli.core.deployment.registry.subprocess.run")
    @mock.patch("ctfcli.core.challenge.Image")
    def test_warns_about_logging_in_with_skip_login(
        self,
        mock_image_constructor: MagicMock,
        mock_subprocess: MagicMock,
        mock_secho: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.build.return_value = "test-challenge"
        mock_image.push.return_value = None

        mock_subprocess.side_effect = [CalledProcessError(1, "")]

        handler = RegistryDeploymentHandler(challenge, host="registry://registry.example.com/example-project")
        result = handler.deploy(skip_login=True)

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_has_calls(
            [
                call(
                    "Skipping registry login because of --skip-login. Make sure you are logged in to the registry.",
                    fg="yellow",
                ),
                call("Could not push image to the registry. Please check docker output above.", fg="red"),
                call(
                    "Remember that you need to manually login to the docker registry when using --skip-login",
                    fg="yellow",
                ),
            ]
        )
