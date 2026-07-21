import click

from ctfcli.core.api import API
from ctfcli.core.config import Config
from ctfcli.core.media import Media


class MediaCommand:
    def add(self, path):
        """Add local media file to config file and remote instance"""
        Media.upload(path)

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
