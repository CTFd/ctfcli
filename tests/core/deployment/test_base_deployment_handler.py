import unittest
from pathlib import Path

from ctfcli.core.challenge import Challenge
from ctfcli.core.deployment import (
    DEPLOYMENT_HANDLERS,
    CloudDeploymentHandler,
    DeploymentHandler,
    RegistryDeploymentHandler,
    SSHDeploymentHandler,
    get_deployment_handler,
    register_deployment_handler,
)
from ctfcli.core.deployment.base import DeploymentResult

BASE_DIR = Path(__file__).parent.parent.parent


class TestDeploymentHandlerLoading(unittest.TestCase):
    def test_get_deployment_handler(self):
        handlers = {
            "cloud": CloudDeploymentHandler,
            "ssh": SSHDeploymentHandler,
            "registry": RegistryDeploymentHandler,
        }

        for key, handler in handlers.items():
            handler_class = get_deployment_handler(key)
            self.assertIs(handlers[key], handler_class)

    def test_register_deployment_handler(self):
        class MyDeploymentHandler(DeploymentHandler):
            def deploy(self, *args, **kwargs) -> DeploymentResult:
                return DeploymentResult(False)

        register_deployment_handler("my-handler", MyDeploymentHandler)
        self.assertIs(DEPLOYMENT_HANDLERS["my-handler"], MyDeploymentHandler)


class TestBaseDeploymentHandler(unittest.TestCase):
    challenge_directory = BASE_DIR / "fixtures" / "challenges" / "test-challenge-dockerfile"
    challenge_path = challenge_directory / "challenge.yml"

    def test_assigns_attributes(self):
        challenge = Challenge(self.challenge_path)
        handler = DeploymentHandler(challenge, "example.com", "https")

        self.assertIs(challenge, handler.challenge)
        self.assertEqual("example.com", handler.host)
        self.assertEqual("https", handler.protocol)

    def test_does_not_implement_deploy(self):
        challenge = Challenge(self.challenge_path)
        handler = DeploymentHandler(challenge, "example.com", "https")

        with self.assertRaises(NotImplementedError):
            handler.deploy()
