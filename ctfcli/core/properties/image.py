import subprocess

from slugify import slugify

from ctfcli.core.exceptions import InvalidChallengeFile
from ctfcli.core.image import Image
from ctfcli.core.properties.base import Property, PropertyContext


class ImageProperty(Property):
    """The challenge image. Only lives in challenge.yml - it is not synced with
    the remote, but used by the deployment handlers. Resolving determines whether
    the image is a registry reference, a local Dockerfile to be built, or a
    pre-built local image."""

    key = "image"
    newline_before = True

    # Well-known registries recognized without an explicit registry:// prefix
    known_registries = [
        "docker.io",
        "gcr.io",
        "ecr.aws",
        "ghcr.io",
        "azurecr.io",
        "registry.digitalocean.com",
        "registry.gitlab.com",
        "registry.ctfd.io",
    ]

    def resolve(self, ctx: PropertyContext) -> Image | None:
        challenge_image = ctx.challenge.get("image")

        if not challenge_image:
            return None

        # Check if challenge_image is explicitly marked with registry:// prefix
        if challenge_image.startswith("registry://"):
            challenge_image = challenge_image.replace("registry://", "")
            return Image(challenge_image)

        # Check if it's a library image
        if challenge_image.startswith("library/"):
            return Image(f"docker.io/{challenge_image}")

        # Check if it defines a known registry
        for registry in self.known_registries:
            if registry in challenge_image:
                return Image(challenge_image)

        # Check if it's a path to dockerfile to be built
        if (ctx.challenge_directory / challenge_image / "Dockerfile").exists():
            return Image(slugify(ctx.challenge["name"]), ctx.challenge_directory / challenge_image)

        # Check if it's a local pre-built image
        if (
            subprocess.call(
                ["docker", "inspect", challenge_image],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            == 0
        ):
            return Image(challenge_image)

        # If the image is set, but we fail to determine whether it's local / remote - raise an exception
        raise InvalidChallengeFile(
            f"Challenge file at {ctx.challenge.challenge_file_path} defines an image, but it couldn't be resolved"
        )
