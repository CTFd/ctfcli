from ctfcli.core.deployment.base import DeploymentHandler
from ctfcli.core.deployment.cloud import CloudDeploymentHandler
from ctfcli.core.deployment.registry import RegistryDeploymentHandler
from ctfcli.core.deployment.ssh import SSHDeploymentHandler

DEPLOYMENT_HANDLERS: dict[str, type[DeploymentHandler]] = {
    "cloud": CloudDeploymentHandler,
    "ssh": SSHDeploymentHandler,
    "registry": RegistryDeploymentHandler,
}


def get_deployment_handler(name: str) -> type[DeploymentHandler]:
    return DEPLOYMENT_HANDLERS[name]


def register_deployment_handler(name: str, handler: type[DeploymentHandler]):
    DEPLOYMENT_HANDLERS[name] = handler
