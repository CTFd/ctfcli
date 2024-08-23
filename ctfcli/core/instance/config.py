from typing import List

from ctfcli.core.api import API
from ctfcli.core.exceptions import InstanceConfigException


class ServerConfig:
    @staticmethod
    def get(key: str) -> str:
        api = API()
        resp = api.get(f"/api/v1/configs/{key}")
        if resp.ok is False:
            raise InstanceConfigException(
                f"Could not get config {key=} because '{resp.content}' with {resp.status_code}"
            )
        resp = resp.json()
        return resp["data"]["value"]

    @staticmethod
    def set(key: str, value: str) -> bool:
        api = API()
        data = {
            "value": value,
        }
        resp = api.patch(f"/api/v1/configs/{key}", json=data)
        if resp.ok is False:
            raise InstanceConfigException(
                f"Could not get config {key=} because '{resp.content}' with {resp.status_code}"
            )
        resp = resp.json()

        return resp["success"]

    @staticmethod
    def getall():
        api = API()
        resp = api.get("/api/v1/configs")
        if resp.ok is False:
            raise InstanceConfigException(f"Could not get configs because '{resp.content}' with {resp.status_code}")
        resp = resp.json()
        configs = resp["data"]

        config = {}
        for c in configs:
            # Ignore alembic_version configs as they are managed by plugins
            if c["key"].endswith("alembic_version") is False:
                config[c["key"]] = c["value"]

        # Not much point in saving internal configs
        del config["ctf_version"]
        del config["version_latest"]
        del config["next_update_check"]
        del config["setup"]

        return config

    @staticmethod
    def setall(configs) -> List[str]:
        failed = []
        for k, v in configs.items():
            try:
                ServerConfig.set(key=k, value=v)
            except InstanceConfigException:
                failed.append(k)
        return failed
