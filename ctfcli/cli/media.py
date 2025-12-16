import os

import click

from ctfcli.core.api import API
from ctfcli.core.config import Config


class MediaCommand:
    def add(self, path):
        """Add local media file to config file and remote instance"""
        config = Config()
        if config.config.has_section("media") is False:
            config.config.add_section("media")

        api = API()

        new_file = ("file", open(path, mode="rb"))  # noqa: SIM115
        filename = os.path.basename(path)
        location = f"media/{filename}"
        file_payload = {
            "type": "page",
            "location": location,
        }

        # Specifically use data= here to send multipart/form-data
        r = api.post("/api/v1/files", files=[new_file], data=file_payload)
        r.raise_for_status()
        resp = r.json()
        server_location = resp["data"][0]["location"]

        # Close the file handle
        new_file[1].close()

        config.config.set("media", location, f"/files/{server_location}")

        with open(config.config_path, "w+") as f:
            config.write(f)

    def rm(self, path):
        """Remove local media file from remote server and local config"""
        config = Config()
        api = API()

        local_location = config["media"][path]

        remote_files = api.get("/api/v1/files?type=page").json()["data"]
        for remote_file in remote_files:
            if f"/files/{remote_file['location']}" == local_location:
                # Delete file from server
                r = api.delete(f"/api/v1/files/{remote_file['id']}")
                r.raise_for_status()

                # Update local config file
                del config["media"][path]
                with open(config.config_path, "w+") as f:
                    config.write(f)

    def url(self, path):
        """Get server URL for a file key"""
        config = Config()
        api = API()

        if config.config.has_section("media") is False:
            config.config.add_section("media")

        try:
            location = config["media"][path]
        except KeyError:
            click.secho(f"Could not locate local media '{path}'", fg="red")
            return 1

        remote_files = api.get("/api/v1/files?type=page").json()["data"]
        for remote_file in remote_files:
            if f"/files/{remote_file['location']}" == location:
                base_url = config["config"]["url"]
                base_url = base_url.rstrip("/")
                return f"{base_url}{location}"
        click.secho(f"Could not locate remote media '{path}'", fg="red")
        return 1
