from typing import Optional

from ctfcli.core.challenge import Challenge


class DeploymentResult:
    def __init__(
        self,
        success: bool,
        domain: Optional[str] = None,
        port: Optional[str] = None,
        connection_info: Optional[str] = None,
    ):
        self.success = success
        self.domain = domain
        self.port = port
        self.connection_info = connection_info


class DeploymentHandler:
    def __init__(self, challenge: Challenge, host: Optional[str] = None, protocol: Optional[str] = None):
        self.challenge = challenge
        self.host = host if host else challenge.get("host", None)
        self.protocol = protocol if protocol else challenge.get("protocol", None)

    def deploy(self, *args, **kwargs) -> DeploymentResult:
        raise NotImplementedError
