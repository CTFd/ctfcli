import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, call

from ctfcli.core.challenge import Challenge
from ctfcli.core.deployment import CloudDeploymentHandler
from ctfcli.core.deployment.base import DeploymentResult

BASE_DIR = Path(__file__).parent.parent.parent


class TestCloudDeployment(unittest.TestCase):
    challenge_directory = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
    challenge_path = challenge_directory / "challenge.yml"

    mock_user_response = {
        "success": True,
        "data": {
            "affiliation": None,
            "oauth_id": None,
            "fields": [],
            "name": "admin",
            "language": None,
            "bracket": None,
            "email": "test@example.com",
            "id": 1,
            "website": None,
            "team_id": 1,
            "place": None,
            "score": 0,
        },
    }

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.cloud.API")
    @mock.patch("ctfcli.core.deployment.cloud.click.secho")
    def test_fails_deployment_if_challenge_does_not_provide_image(self, mock_secho: MagicMock, *args, **kwargs):
        challenge = Challenge(self.challenge_path, {"image": None})

        handler = CloudDeploymentHandler(challenge)
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_secho.assert_called_once_with("Challenge does not define an image to deploy", fg="red")

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.cloud.API")
    @mock.patch("ctfcli.core.deployment.cloud.click.secho")
    def test_fails_deployment_if_instance_does_not_support_deployments(
        self, mock_secho: MagicMock, mock_api_constructor: MagicMock, *args, **kwargs
    ):
        mock_response = MagicMock()
        mock_response.ok = False

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.get.return_value = mock_response

        challenge = Challenge(self.challenge_path)

        handler = CloudDeploymentHandler(challenge)
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        mock_api.get.assert_called_once_with("/api/v1/images")
        mock_secho.assert_called_once_with("Target instance does not support cloud deployments", fg="red")

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.cloud.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    @mock.patch("ctfcli.core.deployment.cloud.API")
    def test_fails_deployment_if_image_build_failed(
        self,
        mock_api_constructor: MagicMock,
        mock_image_constructor: MagicMock,
        mock_secho: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.basename = "test-challenge"
        mock_image.built = False
        mock_image.build.return_value = None

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.prefix_url = "https://example-project.ctfd.io/"
        mock_api.access_token = "deadbeef"

        def mock_get(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.ok = True
            mock_response.json.return_value = {
                "success": True,
                "data": [],
            }
            return mock_response

        mock_api.get.side_effect = mock_get

        handler = CloudDeploymentHandler(challenge)
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/images"),  # check if deployments are supported
                call("/api/v1/images"),  # get image information
            ]
        )

        mock_api.patch.assert_not_called()

        # expect an error message
        mock_secho.assert_called_once_with("Could not build the image. Please check docker output above.", fg="red")

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.cloud.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    @mock.patch("ctfcli.core.deployment.cloud.API")
    def test_fails_deployment_if_image_push_failed(
        self,
        mock_api_constructor: MagicMock,
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
        mock_image.push.return_value = None

        mock_api: MagicMock = mock_api_constructor.return_value

        def mock_get(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.ok = True
            mock_response.json.return_value = {
                "success": True,
                "data": [],
            }
            return mock_response

        mock_api.get.side_effect = mock_get

        handler = CloudDeploymentHandler(challenge)
        result = handler.deploy(skip_login=True)

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/images"),  # check if deployments are supported
                call("/api/v1/images"),  # get image information
            ]
        )

        mock_api.patch.assert_not_called()

        # expect an error message
        mock_secho.assert_has_calls(
            [
                call(
                    "Skipping registry login because of --skip-login. Make sure you are logged in to the registry.",
                    fg="yellow",
                ),
                call("Could not push image to the registry.", fg="red"),
                call(
                    "Remember that you need to manually login to the docker registry when using --skip-login",
                    fg="yellow",
                ),
            ]
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch(
        "ctfcli.core.deployment.cloud.subprocess.check_output",
        return_value=b'Error response from daemon: Get "https://registry.ctfd.io/v2/": unauthorized: authentication required',  # noqa
    )
    @mock.patch("ctfcli.core.deployment.cloud.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    @mock.patch("ctfcli.core.deployment.cloud.API")
    def test_fails_deployment_if_registry_login_unsuccessful(
        self,
        mock_api_constructor: MagicMock,
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

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.prefix_url = "https://example-project.ctfd.io/"
        mock_api.access_token = "deadbeef"

        def mock_get(*args, **kwargs):
            path = args[0]

            if path == "/api/v1/images":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": [],
                }
                return mock_response

            if path == "/api/v1/services":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": [],
                }
                return mock_response

            if path == "/api/v1/users/me":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = self.mock_user_response
                return mock_response

        mock_api.get.side_effect = mock_get

        handler = CloudDeploymentHandler(challenge)
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/images"),  # check if deployments are supported
                call("/api/v1/images"),  # get image information
                call("/api/v1/users/me"),  # get username for registry login
            ]
        )

        mock_api.patch.assert_not_called()

        # check docker registry login
        mock_subprocess.assert_called_once_with(
            ["docker", "login", "-u", "admin@example-project.ctfd.io", "--password-stdin", "registry.ctfd.io"],
            input=b"deadbeef",
            stderr=-1,
        )

        # expect an error message
        mock_secho.assert_called_once_with(
            "Could not log in to the registry. Please check your access token and instance URL", fg="red"
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.cloud.subprocess.check_output")
    @mock.patch("ctfcli.core.deployment.cloud.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    @mock.patch("ctfcli.core.deployment.cloud.API")
    def test_fails_deployment_if_instance_url_is_not_ctfd_assigned(
        self,
        mock_api_constructor: MagicMock,
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

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.prefix_url = "https://custom-project.example.com/"

        def mock_get(*args, **kwargs):
            path = args[0]

            if path == "/api/v1/images":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": [],
                }
                return mock_response

            if path == "/api/v1/services":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": [],
                }
                return mock_response

            if path == "/api/v1/users/me":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = self.mock_user_response
                return mock_response

        mock_api.get.side_effect = mock_get

        handler = CloudDeploymentHandler(challenge)
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/images"),  # check if deployments are supported
                call("/api/v1/images"),  # get image information
                call("/api/v1/users/me"),  # get username for registry login
            ]
        )

        mock_api.patch.assert_not_called()

        # check docker registry login didn't happen
        mock_subprocess.assert_not_called()

        # expect an error message
        mock_secho.assert_has_calls(
            [
                call(
                    "Instance URL is not a CTFd assigned URL. Either use the CTFd assigned domain name, "
                    "or login to the registry manually and deploy with --skip-login",
                    fg="red",
                ),
                call("Could not log in to the registry. Please check your access token and instance URL", fg="red"),
            ]
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.cloud.subprocess.check_output")
    @mock.patch("ctfcli.core.deployment.cloud.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    @mock.patch("ctfcli.core.deployment.cloud.API")
    def test_allows_skipping_registry_login(
        self,
        mock_api_constructor: MagicMock,
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
        mock_image.push.return_value = "registry.ctfd.io/example-project/test-challenge"

        mock_api: MagicMock = mock_api_constructor.return_value

        def mock_get(*args, **kwargs):
            path = args[0]

            if path == "/api/v1/images":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": [
                        {
                            "id": 1,
                            "name": "test-challenge",
                            "status": "pushed",
                            "location": "registry.ctfd.io/example-project/test-challenge",
                        }
                    ],
                }
                return mock_response

            if path == "/api/v1/services":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": [{"id": 1, "name": "test-challenge", "status": "deployed"}],
                }
                return mock_response

            if path == "/api/v1/services/1":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": {
                        "id": 1,
                        "name": "test-challenge",
                        "status": "deployed",
                        "scale": 1,
                        "hostname": "example-project-test-challenge.chals.io",
                        "internal_port": "80",
                        "image": "registry.ctfd.io/example-project/test-challenge:latest",
                        "tcp_hostname": None,
                        "tcp_port": None,
                        "memory_limit": "256 MB",
                    },
                }
                return mock_response

        def mock_patch(*args, **kwargs):
            new_image = kwargs.get("json", {}).get("image", None)

            mock_response = MagicMock()
            mock_response.ok = True
            mock_response.json.return_value = {
                "success": True,
                "data": [
                    {
                        "id": 1,
                        "name": "test-challenge",
                        "status": "deployed",
                        "scale": 1,
                        "hostname": "example-project-test-challenge.chals.io",
                        "internal_port": "80",
                        "image": new_image,
                        "tcp_hostname": None,
                        "tcp_port": None,
                        "memory_limit": "256 MB",
                    }
                ],
            }
            return mock_response

        mock_api.get.side_effect = mock_get
        mock_api.patch.side_effect = mock_patch

        handler = CloudDeploymentHandler(challenge, protocol="https")
        result = handler.deploy(skip_login=True)

        self.assertIsInstance(result, DeploymentResult)
        self.assertTrue(result.success)
        self.assertEqual("https://example-project-test-challenge.chals.io", result.connection_info)

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/images"),  # check if deployments are supported
                call("/api/v1/images"),  # get image information
                call("/api/v1/services"),  # get existing services
                call("/api/v1/services/1"),  # get service information & check deployment status
            ]
        )

        mock_api.patch.assert_has_calls(
            [
                # update service image
                call("/api/v1/services/1", json={"image": "registry.ctfd.io/example-project/test-challenge"})
            ]
        )

        # check docker registry login didn't happen
        mock_subprocess.assert_not_called()

        # expect a warning for skip_login
        mock_secho.assert_called_once_with(
            "Skipping registry login because of --skip-login. Make sure you are logged in to the registry.",
            fg="yellow",
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.cloud.subprocess.check_output", return_value=b"Login Succeeded")
    @mock.patch("ctfcli.core.deployment.cloud.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    @mock.patch("ctfcli.core.deployment.cloud.API")
    def test_deploys_challenge_with_existing_image_service(
        self,
        mock_api_constructor: MagicMock,
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
        mock_image.push.return_value = "registry.ctfd.io/example-project/test-challenge"

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.prefix_url = "https://example-project.ctfd.io/"
        mock_api.access_token = "deadbeef"

        def mock_get(*args, **kwargs):
            path = args[0]

            if path == "/api/v1/images":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": [
                        {
                            "id": 1,
                            "name": "test-challenge",
                            "status": "pushed",
                            "location": "registry.ctfd.io/example-project/test-challenge",
                        }
                    ],
                }
                return mock_response

            if path == "/api/v1/services":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": [{"id": 1, "name": "test-challenge", "status": "deployed"}],
                }
                return mock_response

            if path == "/api/v1/services/1":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": {
                        "id": 1,
                        "name": "test-challenge",
                        "status": "deployed",
                        "scale": 1,
                        "hostname": "example-project-test-challenge.chals.io",
                        "internal_port": "80",
                        "image": "registry.ctfd.io/example-project/test-challenge:latest",
                        "tcp_hostname": None,
                        "tcp_port": None,
                        "memory_limit": "256 MB",
                    },
                }
                return mock_response

            if path == "/api/v1/users/me":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = self.mock_user_response
                return mock_response

        def mock_patch(*args, **kwargs):
            new_image = kwargs.get("json", {}).get("image", None)

            mock_response = MagicMock()
            mock_response.ok = True
            mock_response.json.return_value = {
                "success": True,
                "data": [
                    {
                        "id": 1,
                        "name": "test-challenge",
                        "status": "deployed",
                        "scale": 1,
                        "hostname": "example-project-test-challenge.chals.io",
                        "internal_port": "80",
                        "image": new_image,
                        "tcp_hostname": None,
                        "tcp_port": None,
                        "memory_limit": "256 MB",
                    }
                ],
            }
            return mock_response

        mock_api.get.side_effect = mock_get
        mock_api.patch.side_effect = mock_patch

        handler = CloudDeploymentHandler(challenge)
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertTrue(result.success)
        self.assertEqual("https://example-project-test-challenge.chals.io", result.connection_info)

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/images"),  # check if deployments are supported
                call("/api/v1/images"),  # get image information
                call("/api/v1/users/me"),  # get username for registry login
                call("/api/v1/services"),  # get existing services
                call("/api/v1/services/1"),  # get service information & check deployment status
            ]
        )

        mock_api.patch.assert_has_calls(
            [
                # update service image
                call("/api/v1/services/1", json={"image": "registry.ctfd.io/example-project/test-challenge"})
            ]
        )

        # check docker registry login
        mock_subprocess.assert_called_once_with(
            ["docker", "login", "-u", "admin@example-project.ctfd.io", "--password-stdin", "registry.ctfd.io"],
            input=b"deadbeef",
            stderr=-1,
        )

        # do not expect a call to secho as in this case the mocked deployment is instant
        mock_secho.assert_not_called()

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.cloud.subprocess.check_output", return_value=b"Login Succeeded")
    @mock.patch("ctfcli.core.deployment.cloud.time.sleep")
    @mock.patch("ctfcli.core.deployment.cloud.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    @mock.patch("ctfcli.core.deployment.cloud.API")
    def test_deploys_challenge_with_new_image_service(
        self,
        mock_api_constructor: MagicMock,
        mock_image_constructor: MagicMock,
        mock_secho: MagicMock,
        mock_sleep: MagicMock,
        mock_subprocess: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image: MagicMock = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.basename = "test-challenge"
        mock_image.build.return_value = "test-challenge"
        mock_image.push.return_value = "registry.ctfd.io/example-project/test-challenge"

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.prefix_url = "https://example-project.ctfd.io/"
        mock_api.access_token = "deadbeef"

        # return a deployed service response on the 3rd status check
        service_status_responses = [
            {
                "success": True,
                "data": {
                    "id": 1,
                    "name": "test-challenge",
                    "status": "built",
                    "scale": None,
                    "hostname": None,
                    "internal_port": None,
                    "image": None,
                    "tcp_hostname": None,
                    "tcp_port": None,
                    "memory_limit": None,
                },
            },
            {
                "success": True,
                "data": {
                    "id": 1,
                    "name": "test-challenge",
                    "status": "built",
                    "scale": None,
                    "hostname": None,
                    "internal_port": None,
                    "image": None,
                    "tcp_hostname": None,
                    "tcp_port": None,
                    "memory_limit": None,
                },
            },
            {
                "success": True,
                "data": {
                    "id": 1,
                    "name": "test-challenge",
                    "status": "deployed",
                    "scale": 1,
                    "hostname": "example-project-test-challenge.chals.io",
                    "image": "registry.ctfd.io/example-project/test-challenge",
                    "internal_port": 80,
                    "tcp_hostname": None,
                    "tcp_port": None,
                    "memory_limit": "256 MB",
                },
            },
        ]

        def mock_get(*args, **kwargs):
            path = args[0]

            if path == "/api/v1/images":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {"success": True, "data": []}
                return mock_response

            if path == "/api/v1/services":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {"success": True, "data": []}
                return mock_response

            if path == "/api/v1/services/1":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = service_status_responses.pop(0)
                return mock_response

            if path == "/api/v1/users/me":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = self.mock_user_response
                return mock_response

        def mock_post(*args, **kwargs):
            path = args[0]

            if path == "/api/v1/images":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": {
                        "id": 1,
                        "name": "test-challenge",
                        "status": None,
                        "location": "registry.ctfd.io/example-project/test-challenge",
                    },
                }
                return mock_response

            if path == "/api/v1/services":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": {
                        "id": 1,
                        "name": "test-challenge",
                        "status": "built",
                        "scale": None,
                        "hostname": None,
                        "internal_port": None,
                        "image": None,
                        "tcp_hostname": None,
                        "tcp_port": None,
                        "memory_limit": None,
                    },
                }
                return mock_response

        mock_api.get.side_effect = mock_get
        mock_api.post.side_effect = mock_post

        handler = CloudDeploymentHandler(challenge)
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertTrue(result.success)
        self.assertEqual("https://example-project-test-challenge.chals.io", result.connection_info)

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/images"),  # check if deployments are supported
                call("/api/v1/images"),  # get existing images
                call("/api/v1/users/me"),  # get user data for registry login
                call("/api/v1/services"),  # get existing services
                call("/api/v1/services/1"),  # get service information & check deployment status (1st)
                call("/api/v1/services/1"),  # await service deployment #1 (2nd)
                call("/api/v1/services/1"),  # await service deployment #2 (3rd) - should be deployed
            ]
        )

        mock_api.post.assert_has_calls(
            [
                call("/api/v1/images", json={"name": "test-challenge"}),
                call(
                    "/api/v1/services",
                    json={"name": "test-challenge", "image": "registry.ctfd.io/example-project/test-challenge"},
                ),
            ]
        )

        mock_secho.assert_has_calls(
            [
                call("Awaiting service deployment [0/180s]", fg="yellow"),
                call("Awaiting service deployment [10/180s]", fg="yellow"),
            ]
        )

        mock_sleep.assert_has_calls(
            [
                call(10),
                call(10),
            ]
        )

        # check docker registry login
        mock_subprocess.assert_called_once_with(
            ["docker", "login", "-u", "admin@example-project.ctfd.io", "--password-stdin", "registry.ctfd.io"],
            input=b"deadbeef",
            stderr=-1,
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.cloud.subprocess.check_output", return_value=b"Login Succeeded")
    @mock.patch("ctfcli.core.deployment.cloud.time.sleep")
    @mock.patch("ctfcli.core.deployment.cloud.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    @mock.patch("ctfcli.core.deployment.cloud.API")
    def test_fails_deployment_after_timeout(
        self,
        mock_api_constructor: MagicMock,
        mock_image_constructor: MagicMock,
        mock_secho: MagicMock,
        mock_sleep: MagicMock,
        mock_subprocess: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path)

        mock_image = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.basename = "test-challenge"
        mock_image.build.return_value = "test-challenge"
        mock_image.push.return_value = "registry.ctfd.io/example-project/test-challenge"

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.prefix_url = "https://example-project.ctfd.io/"
        mock_api.access_token = "deadbeef"

        def mock_get(*args, **kwargs):
            path = args[0]

            if path == "/api/v1/images":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {"success": True, "data": []}
                return mock_response

            if path == "/api/v1/services":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {"success": True, "data": []}
                return mock_response

            if path == "/api/v1/services/1":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": {
                        "id": 1,
                        "name": "test-challenge",
                        "status": "built",
                        "scale": None,
                        "hostname": None,
                        "internal_port": None,
                        "image": None,
                        "tcp_hostname": None,
                        "tcp_port": None,
                        "memory_limit": None,
                    },
                }
                return mock_response

            if path == "/api/v1/users/me":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = self.mock_user_response
                return mock_response

        def mock_post(*args, **kwargs):
            path = args[0]

            if path == "/api/v1/images":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": {
                        "id": 1,
                        "name": "test-challenge",
                        "status": None,
                        "location": "registry.ctfd.io/example-project/test-challenge",
                    },
                }
                return mock_response

            if path == "/api/v1/services":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": {
                        "id": 1,
                        "name": "test-challenge",
                        "status": "built",
                        "scale": None,
                        "hostname": None,
                        "internal_port": None,
                        "image": None,
                        "tcp_hostname": None,
                        "tcp_port": None,
                        "memory_limit": None,
                    },
                }
                return mock_response

        mock_api.get.side_effect = mock_get
        mock_api.post.side_effect = mock_post

        handler = CloudDeploymentHandler(challenge)
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertFalse(result.success)
        self.assertIsNone(result.connection_info)

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/images"),  # check if deployments are supported
                call("/api/v1/images"),  # get existing images
                call("/api/v1/users/me"),  # get user data
                call("/api/v1/services"),  # get existing services
                call("/api/v1/services/1"),  # get service information & check deployment status
                call("/api/v1/services/1"),  # await service deployment #1
                call("/api/v1/services/1"),  # await service deployment #2
            ]
        )

        mock_api.post.assert_has_calls(
            [
                call("/api/v1/images", json={"name": "test-challenge"}),
                call(
                    "/api/v1/services",
                    json={"name": "test-challenge", "image": "registry.ctfd.io/example-project/test-challenge"},
                ),
            ]
        )

        mock_secho.assert_has_calls(
            [
                call("Awaiting service deployment [0/180s]", fg="yellow"),
                call("Awaiting service deployment [10/180s]", fg="yellow"),
                call("Awaiting service deployment [20/180s]", fg="yellow"),
                call("Awaiting service deployment [30/180s]", fg="yellow"),
                call("Awaiting service deployment [40/180s]", fg="yellow"),
                call("Awaiting service deployment [50/180s]", fg="yellow"),
                call("Awaiting service deployment [60/180s]", fg="yellow"),
                call("Awaiting service deployment [70/180s]", fg="yellow"),
                call("Awaiting service deployment [80/180s]", fg="yellow"),
                call("Awaiting service deployment [90/180s]", fg="yellow"),
                call("Awaiting service deployment [100/180s]", fg="yellow"),
                call("Awaiting service deployment [110/180s]", fg="yellow"),
                call("Awaiting service deployment [120/180s]", fg="yellow"),
                call("Awaiting service deployment [130/180s]", fg="yellow"),
                call("Awaiting service deployment [140/180s]", fg="yellow"),
                call("Awaiting service deployment [150/180s]", fg="yellow"),
                call("Awaiting service deployment [160/180s]", fg="yellow"),
                call("Awaiting service deployment [170/180s]", fg="yellow"),
                call("Timeout awaiting challenge deployment", fg="red"),
            ]
        )

        mock_sleep.assert_has_calls(
            [
                call(10),
                call(10),
                call(10),
                call(10),
                call(10),
                call(10),
                call(10),
                call(10),
                call(10),
                call(10),
                call(10),
                call(10),
                call(10),
                call(10),
                call(10),
                call(10),
                call(10),
                call(10),
            ]
        )

        # check docker registry login
        mock_subprocess.assert_called_once_with(
            ["docker", "login", "-u", "admin@example-project.ctfd.io", "--password-stdin", "registry.ctfd.io"],
            input=b"deadbeef",
            stderr=-1,
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    @mock.patch("ctfcli.core.deployment.cloud.subprocess.check_output", return_value=b"Login Succeeded")
    @mock.patch("ctfcli.core.deployment.cloud.click.secho")
    @mock.patch("ctfcli.core.challenge.Image")
    @mock.patch("ctfcli.core.deployment.cloud.API")
    def test_exposes_tcp_port(
        self,
        mock_api_constructor: MagicMock,
        mock_image_constructor: MagicMock,
        mock_secho: MagicMock,
        mock_subprocess: MagicMock,
        *args,
        **kwargs,
    ):
        challenge = Challenge(self.challenge_path, {"protocol": "tcp"})

        mock_image = mock_image_constructor.return_value
        mock_image.name = "test-challenge"
        mock_image.basename = "test-challenge"
        mock_image.build.return_value = "test-challenge"
        mock_image.push.return_value = "registry.ctfd.io/example-project/test-challenge"

        mock_api: MagicMock = mock_api_constructor.return_value
        mock_api.prefix_url = "https://example-project.ctfd.io/"
        mock_api.access_token = "deadbeef"

        service_status_responses = [
            {
                "success": True,
                "data": {
                    "id": 1,
                    "name": "test-challenge",
                    "status": "deployed",
                    "scale": 1,
                    "hostname": "example-project-test-challenge.chals.io",
                    "internal_port": "80",
                    "image": "registry.ctfd.io/example-project/test-challenge:latest",
                    "tcp_hostname": None,
                    "tcp_port": None,
                    "memory_limit": "256 MB",
                },
            },
            {
                "success": True,
                "data": {
                    "id": 1,
                    "name": "test-challenge",
                    "status": "deployed",
                    "scale": 1,
                    "hostname": "example-project-test-challenge.chals.io",
                    "internal_port": "80",
                    "image": "registry.ctfd.io/example-project/test-challenge:latest",
                    "tcp_hostname": "0.cloud.chals.io",
                    "tcp_port": "31900",
                    "memory_limit": "256 MB",
                },
            },
        ]

        def mock_get(*args, **kwargs):
            path = args[0]

            if path == "/api/v1/images":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": [
                        {
                            "id": 1,
                            "name": "test-challenge",
                            "status": "pushed",
                            "location": "registry.ctfd.io/example-project/test-challenge",
                        }
                    ],
                }
                return mock_response

            if path == "/api/v1/services":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = {
                    "success": True,
                    "data": [{"id": 1, "name": "test-challenge", "status": "deployed"}],
                }
                return mock_response

            if path == "/api/v1/services/1":
                mock_response = MagicMock()
                mock_response.ok = True

                mock_response.json.return_value = service_status_responses.pop(0)
                return mock_response

            if path == "/api/v1/users/me":
                mock_response = MagicMock()
                mock_response.ok = True
                mock_response.json.return_value = self.mock_user_response
                return mock_response

        def mock_patch(*args, **kwargs):
            new_image = kwargs.get("json").get("image")

            mock_response = MagicMock()
            mock_response.ok = True
            mock_response.json.return_value = {
                "success": True,
                "data": {
                    "id": 1,
                    "name": "test-challenge",
                    "status": "deployed",
                    "scale": 1,
                    "hostname": "example-project-test-challenge.chals.io",
                    "internal_port": "80",
                    "image": new_image,
                    "tcp_hostname": None,
                    "tcp_port": None,
                    "memory_limit": "256 MB",
                },
            }

            return mock_response

        mock_api.get.side_effect = mock_get
        mock_api.patch.side_effect = mock_patch

        handler = CloudDeploymentHandler(challenge)
        result = handler.deploy()

        self.assertIsInstance(result, DeploymentResult)
        self.assertTrue(result.success)
        self.assertEqual("nc 0.cloud.chals.io 31900", result.connection_info)

        mock_api.get.assert_has_calls(
            [
                call("/api/v1/images"),  # check if deployments are supported
                call("/api/v1/images"),  # get image information
                call("/api/v1/users/me"),  # get user data
                call("/api/v1/services"),  # get existing services
                call("/api/v1/services/1"),  # get service information & check deployment status
            ]
        )

        mock_api.patch.assert_has_calls(
            [
                # update service image
                call("/api/v1/services/1", json={"image": "registry.ctfd.io/example-project/test-challenge"}),
                # expose TCP port
                call("/api/v1/services/1", json={"expose": True}),
            ]
        )

        # do not expect a call to secho as in this case the mocked deployment is instant
        mock_secho.assert_not_called()

        # check docker registry login
        mock_subprocess.assert_called_once_with(
            ["docker", "login", "-u", "admin@example-project.ctfd.io", "--password-stdin", "registry.ctfd.io"],
            input=b"deadbeef",
            stderr=-1,
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    def test_get_connection_info(self, *args, **kwargs):
        challenge = Challenge(self.challenge_path)
        handler = CloudDeploymentHandler(challenge, protocol="http")

        self.assertEqual(
            "https://example-project-test-challenge.ctfd.io",
            handler._get_connection_info("example-project-test-challenge.ctfd.io"),
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=challenge_directory)
    def test_get_connection_info_tcp(self, *args, **kwargs):
        challenge = Challenge(self.challenge_path)
        handler = CloudDeploymentHandler(challenge, protocol="tcp")

        self.assertEqual(
            "nc 0.cloud.chals.io 30054",
            handler._get_connection_info(
                "example-project-test-challenge.ctfd.io", tcp_hostname="0.cloud.chals.io", tcp_port="30054"
            ),
        )

    @mock.patch(
        "ctfcli.core.config.Path.cwd", return_value=BASE_DIR / "fixtures" / "challenges" / "test-challenge-minimal"
    )
    def test_get_connection_info_fallback(self, *args, **kwargs):
        # test with a challenge that does not define a protocol
        minimal_challenge = BASE_DIR / "fixtures" / "challenges" / "test-challenge-minimal" / "challenge.yml"

        challenge = Challenge(minimal_challenge)
        handler = CloudDeploymentHandler(challenge)

        self.assertEqual(
            "example-project-test-challenge.ctfd.io",
            handler._get_connection_info("example-project-test-challenge.ctfd.io"),
        )
