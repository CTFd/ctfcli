from typing import Dict, Type

from ctfcli.core.deployment.base import DeploymentHandler
from ctfcli.core.deployment.cloud import CloudDeploymentHandler
from ctfcli.core.deployment.registry import RegistryDeploymentHandler
from ctfcli.core.deployment.ssh import SSHDeploymentHandler

DEPLOYMENT_HANDLERS: Dict[str, Type[DeploymentHandler]] = {
    "cloud": CloudDeploymentHandler,
    "ssh": SSHDeploymentHandler,
    "registry": RegistryDeploymentHandler,
}


def get_deployment_handler(name: str) -> Type[DeploymentHandler]:
    return DEPLOYMENT_HANDLERS[name]


def register_deployment_handler(name: str, handler: Type[DeploymentHandler]):
    DEPLOYMENT_HANDLERS[name] = handler
