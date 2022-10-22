import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from ctfcli.utils.images import build_image, export_image, get_exposed_ports


def ssh(challenge, host):
    # Build image
    image_name = build_image(challenge=challenge)
    print(f"Built {image_name}")

    # Export image to a file
    image_path = export_image(challenge=challenge)
    print(f"Exported {image_name} to {image_path}")
    filename = Path(image_path).name

    # Transfer file to SSH host
    print(f"Transferring {image_path} to {host}")
    host = urlparse(host)
    folder = host.path or "/tmp"
    target_file = f"{folder}/{filename}"
    exposed_port = get_exposed_ports(challenge=challenge)
    domain = host.netloc[host.netloc.find("@") + 1 :]
    subprocess.run(["scp", image_path, f"{host.netloc}:{target_file}"])
    subprocess.run(
        ["ssh", host.netloc, f"docker load -i {target_file} && rm {target_file}"]
    )
    subprocess.run(
        [
            "ssh",
            host.netloc,
            f"docker run -d -p{exposed_port}:{exposed_port} --name {image_name} --restart always {image_name}",
        ]
    )

    # Clean up files
    os.remove(image_path)
    print(f"Cleaned up {image_path}")

    return True, domain, exposed_port


def registry(challenge, host):
    # Build image
    image_name = build_image(challenge=challenge)
    print(f"Built {image_name}")
    url = urlparse(host)
    tag = f"{url.netloc}{url.path}"
    subprocess.call(["docker", "tag", image_name, tag])
    subprocess.call(["docker", "push", tag])


DEPLOY_HANDLERS = {"ssh": ssh, "registry": registry}
