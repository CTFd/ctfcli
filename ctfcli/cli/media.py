import os

import click

from ctfcli.core.api import API
from ctfcli.core.config import Config
from ctfcli.core.media import Media
from ctfcli.utils.hashing import hash_file


class MediaCommand:
    def add(self, path):
        """Add local media file to config file and remote instance"""
        config = Config()
        if config.config.has_section("media") is False:
            config.config.add_section("media")

        api = API()

        filename = os.path.basename(path)
        location = f"media/{filename}"
        server_location = Media.upload(api, path, location)

        config.config.set("media", location, f"/files/{server_location}")

        with open(config.config_path, "w+") as f:
            config.write(f)

    def sync(self):
        """Sync all local media files in the media folder to the remote instance"""
        config = Config()
        if config.config.has_section("media") is False:
            config.config.add_section("media")

        media_path = config.project_path / "media"
        if not media_path.is_dir():
            click.secho(f"Could not locate media folder '{media_path}'", fg="red")
            return 1

        api = API()

        r = api.get("/api/v1/files?type=page")
        r.raise_for_status()
        remote_files = {f"/files/{f['location']}": f for f in r.json()["data"]}

        for local_file in sorted(media_path.rglob("*")):
            if not local_file.is_file() or local_file.name.startswith("."):
                continue

            location = f"media/{local_file.relative_to(media_path).as_posix()}"
            remote_file = remote_files.get(config["media"].get(location))

            if remote_file:
                with open(local_file, mode="rb") as file_handle:
                    local_sha1sum = hash_file(file_handle)

                if remote_file.get("sha1sum") == local_sha1sum:
                    click.secho(f"Skipping unchanged media '{location}'", fg="yellow")
                    continue

                r = api.delete(f"/api/v1/files/{remote_file['id']}")
                r.raise_for_status()

            server_location = Media.upload(api, local_file, location)
            config.config.set("media", location, f"/files/{server_location}")
            click.secho(f"Synced media '{location}'", fg="green")

        with open(config.config_path, "w+") as f:
            config.write(f)

        return 0

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
