from pathlib import Path

from ctfcli.core.api import API
from ctfcli.core.config import Config
from ctfcli.core.exceptions import ProjectNotInitialized
from ctfcli.utils.tools import safe_format


class Media:
    @staticmethod
    def upload(path) -> str:
        config = Config()
        if config.config.has_section("media") is False:
            config.config.add_section("media")

        api = API()

        path = Path(path)
        filename = path.name
        new_file = (filename, path.open(mode="rb"))
        location = f"media/{filename}"
        file_payload = {
            "type": "page",
            "location": location,
        }

        try:
            # Specifically use data= here to send multipart/form-data
            r = api.post("/api/v1/files", files={"file": new_file}, data=file_payload)
            r.raise_for_status()
            resp = r.json()
            server_location = resp["data"][0]["location"]
        finally:
            new_file[1].close()

        media_url = f"/files/{server_location}"
        config.config.set("media", location, media_url)

        with open(config.config_path, "w+") as f:
            config.write(f)

        return media_url

    @staticmethod
    def replace_placeholders(content: str) -> str:
        try:
            config = Config()
            section = config["media"]
        except (KeyError, ProjectNotInitialized):
            section = []
        for m in section:
            content = safe_format(content, items={m: config["media"][m]})
        return content
