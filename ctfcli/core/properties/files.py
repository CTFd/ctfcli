from pathlib import Path

import click

from ctfcli.core.exceptions import InvalidChallengeFile
from ctfcli.core.properties.base import Property, PropertyContext
from ctfcli.utils.hashing import hash_file


class FilesProperty(Property):
    """Distributed challenge files. Created in bulk on create; synced with a
    diff against the remote (using sha1sums when the CTFd version provides them)
    to avoid re-uploading unchanged files.

    Note: files are deliberately not part of pull() / the normalized challenge -
    mirror() and verify() handle them separately, because downloading is only
    wanted in some flows.
    """

    key = "files"
    newline_before = True
    op_order = 40

    def is_default(self, value) -> bool:
        return value == []

    def validate(self, ctx: PropertyContext) -> None:
        files = ctx.challenge.get("files") or []
        for challenge_file in files:
            if not (ctx.challenge_directory / challenge_file).exists():
                raise InvalidChallengeFile(f"File {challenge_file} could not be loaded")

    def create(self, ctx: PropertyContext) -> None:
        if ctx.challenge.get("files") and not self.ignored(ctx):
            self.create_all_files(ctx)

    def sync(self, ctx: PropertyContext) -> None:
        if self.ignored(ctx):
            return

        ctx.challenge["files"] = ctx.challenge.get("files") or []
        ctx.remote_challenge["files"] = ctx.remote_challenge.get("files") or []

        # Get basenames of local files to compare against remote files
        local_files = {f.split("/")[-1]: f for f in ctx.challenge["files"]}
        remote_files = self.normalize_remote_files(ctx.remote_challenge["files"])

        # Delete remote files which are no longer defined locally
        for remote_file in remote_files:
            if remote_file not in local_files:
                self.delete_file(ctx, remote_files[remote_file]["location"])

        # Only check for file changes if there are files to upload
        if not local_files:
            return

        sha1sums = self.get_files_sha1sums(ctx)
        for local_file_name in local_files:
            # Creating a new file
            if local_file_name not in remote_files:
                self.create_file(ctx, ctx.challenge_directory / local_files[local_file_name])
                continue

            # Updating an existing file
            # sha1sum is present in CTFd 3.7+, use it instead of always re-uploading the file if possible
            remote_file_sha1sum = sha1sums[remote_files[local_file_name]["location"]]
            if remote_file_sha1sum is not None:
                with open(ctx.challenge_directory / local_files[local_file_name], "rb") as lf:
                    local_file_sha1sum = hash_file(lf)

                # Allow users to specify sha1sum in ignore to force reuploads
                if "sha1sum" not in ctx.ignore and local_file_sha1sum == remote_file_sha1sum:
                    continue

            # if sha1sums are not present, or the hashes are different, re-upload the file
            self.delete_file(ctx, remote_files[local_file_name]["location"])
            self.create_file(ctx, ctx.challenge_directory / local_files[local_file_name])

    def mirror(self, ctx: PropertyContext, normalized: dict) -> None:
        if self.ignored(ctx):
            return

        ctx.remote_challenge["files"] = ctx.remote_challenge.get("files") or []
        normalized["files"] = normalized.get("files") or []

        files_directory_name = ctx.options.get("files_directory_name", "dist")
        local_files = {Path(f).name: f for f in normalized["files"]}

        # Update files
        for remote_file in ctx.remote_challenge["files"]:
            # Get base file name
            remote_file_name = remote_file.split("/")[-1].split("?token=")[0]

            # The file is only present on the remote - we have to download it, and assume a path
            if remote_file_name not in local_files:
                r = ctx.api.get(remote_file)
                r.raise_for_status()

                # Ensure the directory for the challenge files exists
                challenge_files_directory = ctx.challenge_directory / files_directory_name
                challenge_files_directory.mkdir(parents=True, exist_ok=True)

                (challenge_files_directory / remote_file_name).write_bytes(r.content)
                normalized["files"].append(f"{files_directory_name}/{remote_file_name}")

            # The file is already present in the challenge.yml - we know the desired path
            else:
                r = ctx.api.get(remote_file)
                r.raise_for_status()
                (ctx.challenge_directory / local_files[remote_file_name]).write_bytes(r.content)

        # Soft-Delete files that are not present on the remote
        # Remove them from challenge.yml but do not delete them from disk
        remote_file_names = [f.split("/")[-1].split("?token=")[0] for f in ctx.remote_challenge["files"]]
        normalized["files"] = [f for f in normalized["files"] if Path(f).name in remote_file_names]

    def verify(self, ctx: PropertyContext) -> bool:
        if self.ignored(ctx):
            return True

        ctx.challenge["files"] = ctx.challenge.get("files") or []
        ctx.remote_challenge["files"] = ctx.remote_challenge.get("files") or []

        # Check if files defined in challenge.yml are present
        try:
            self.validate(ctx)
            local_files = {Path(f).name: f for f in ctx.challenge["files"]}
        except InvalidChallengeFile:
            click.secho(
                "InvalidChallengeFile",
                fg="yellow",
            )
            return False

        remote_files = self.normalize_remote_files(ctx.remote_challenge["files"])
        # Check if there are no extra local files
        for local_file in local_files:
            if local_file not in remote_files:
                click.secho(
                    f"{local_file} is not in remote challenge.",
                    fg="yellow",
                )
                return False

        sha1sums = self.get_files_sha1sums(ctx)
        # Check if all remote files are present locally
        for remote_file_name in remote_files:
            if remote_file_name not in local_files:
                click.secho(
                    f"{remote_file_name} is not in local challenge.",
                    fg="yellow",
                )
                return False

            # sha1sum is present in CTFd 3.7+, use it instead of downloading the file if possible
            remote_file_sha1sum = sha1sums[remote_files[remote_file_name]["location"]]
            if remote_file_sha1sum is not None:
                with open(ctx.challenge_directory / local_files[remote_file_name], "rb") as lf:
                    local_file_sha1sum = hash_file(lf)

                if local_file_sha1sum != remote_file_sha1sum:
                    click.secho(
                        "sha1sum does not match with remote one.",
                        fg="yellow",
                    )
                    return False

                continue

            # If sha1sum is not present, download the file and compare the contents
            r = ctx.api.get(remote_files[remote_file_name]["url"])
            r.raise_for_status()
            remote_file_contents = r.content
            local_file_contents = (ctx.challenge_directory / local_files[remote_file_name]).read_bytes()

            if remote_file_contents != local_file_contents:
                click.secho(
                    "the file content does not match with the remote one.",
                    fg="yellow",
                )
                return False

        return True

    def delete_file(self, ctx: PropertyContext, remote_location: str) -> None:
        remote_files = ctx.api.get("/api/v1/files?type=challenge").json()["data"]

        for remote_file in remote_files:
            if remote_file["location"] == remote_location:
                r = ctx.api.delete(f"/api/v1/files/{remote_file['id']}")
                r.raise_for_status()

    def create_file(self, ctx: PropertyContext, local_path: Path) -> None:
        file_payload = {"challenge_id": ctx.challenge_id, "type": "challenge"}

        with local_path.open(mode="rb") as file_handle:
            # Specifically use data= here to send multipart/form-data
            r = ctx.api.post("/api/v1/files", files={"file": (local_path.name, file_handle)}, data=file_payload)
            r.raise_for_status()

    def create_all_files(self, ctx: PropertyContext) -> None:
        new_files = []
        for challenge_file in ctx.challenge["files"]:
            file_path = ctx.challenge_directory / challenge_file
            new_files.append(("file", (file_path.name, file_path.open("rb"))))

        files_payload = {"challenge_id": ctx.challenge_id, "type": "challenge"}

        # Specifically use data= here to send multipart/form-data
        r = ctx.api.post("/api/v1/files", files=new_files, data=files_payload)
        r.raise_for_status()

        # Close the file handles
        for file_payload in new_files:
            file_payload[1][1].close()

    # Create a dictionary of remote files in { basename: {"url": "", "location": ""} } format
    @staticmethod
    def normalize_remote_files(remote_files: list[str]) -> dict[str, dict[str, str]]:
        normalized = {}
        for f in remote_files:
            file_parts = f.split("?token=")[0].split("/")
            normalized[file_parts[-1]] = {
                "url": f,
                "location": f"{file_parts[-2]}/{file_parts[-1]}",
            }

        return normalized

    # Create a dictionary of sha1sums in { location: sha1sum } format
    @staticmethod
    def get_files_sha1sums(ctx: PropertyContext) -> dict[str, str]:
        r = ctx.api.get("/api/v1/files?type=challenge")
        r.raise_for_status()
        return {f["location"]: f.get("sha1sum", None) for f in r.json()["data"]}
