import os
import subprocess
import time
import click
from pathlib import Path
from urllib.parse import urlparse
from slugify import slugify
from ctfcli.utils.config import generate_session

from ctfcli.utils.images import (
    build_image,
    export_image,
    get_exposed_ports,
    push_image,
)


def format_connection_info(protocol, hostname, tcp_hostname, tcp_port):
    if protocol is None:
        connection_info = hostname
    elif protocol.startswith("http"):
        connection_info = f"{protocol}://{hostname}"
    elif protocol == "tcp":
        connection_info = f"nc {tcp_hostname} {tcp_port}"
    else:
        connection_info = hostname

    return connection_info


def ssh(challenge, host, protocol):
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

    status = True
    domain = domain
    port = exposed_port
    connect_info = format_connection_info(
        protocol=protocol, hostname=domain, tcp_hostname=domain, tcp_port=port,
    )
    return status, domain, port, connect_info


def registry(challenge, host, protocol):
    # Build image
    image_name = build_image(challenge=challenge)
    url = urlparse(host)
    tag = f"{url.netloc}{url.path}"
    push_image(local_tag=image_name, location=tag)
    status = True
    domain = ""
    port = ""
    connect_info = format_connection_info(
        protocol=protocol, hostname=domain, tcp_hostname=domain, tcp_port=port,
    )
    return status, domain, port, connect_info


def cloud(challenge, host, protocol):
    name = challenge["name"]
    slug = slugify(name)

    s = generate_session()
    # Detect whether we have the appropriate endpoints
    check = s.get("/api/v1/images", json=True)
    if check.ok is False:
        click.secho(
            "Target instance does not have deployment endpoints", fg="red",
        )
        return False, None, None, None

    # Try to find an appropriate image.
    images = s.get("/api/v1/images", json=True).json()["data"]
    image = None
    for i in images:
        if i["location"].endswith(f"/{slug}"):
            image = i
            break
    else:
        # Create the image if we did not find it.
        image = s.post("/api/v1/images", json={"name": slug}).json()["data"]

    # Build image
    image_name = build_image(challenge=challenge)
    location = image["location"]

    # TODO: Authenticate to Registry

    # Push image
    push_image(image_name, location)

    # Look for existing service
    services = s.get("/api/v1/services", json=True).json()["data"]
    service = None
    for srv in services:
        if srv["name"] == slug:
            service = srv
            # Update the service
            s.patch(
                f"/api/v1/services/{service['id']}", json={"image": location}
            ).raise_for_status()
            service = s.get(f"/api/v1/services/{service['id']}", json=True).json()[
                "data"
            ]
            break
    else:
        # Could not find the service. Create it using our pushed image.
        # Deploy the image by creating service
        service = s.post(
            "/api/v1/services", json={"name": slug, "image": location,},
        ).json()["data"]

    # Get connection details
    service_id = service["id"]
    service = s.get(f"/api/v1/services/{service_id}", json=True).json()["data"]

    DEPLOY_TIMEOUT = 180
    while service["hostname"] is None and DEPLOY_TIMEOUT > 0:
        click.secho(
            "Waiting for challenge hostname", fg="yellow",
        )
        service = s.get(f"/api/v1/services/{service_id}", json=True).json()["data"]
        DEPLOY_TIMEOUT -= 10
        time.sleep(10)

    if DEPLOY_TIMEOUT == 0:
        click.secho(
            "Timeout waiting for challenge to deploy", fg="red",
        )
        return False, None, None, None

    # Expose port if we are using tcp
    if protocol == "tcp":
        service = s.patch(f"/api/v1/services/{service['id']}", json={"expose": True})
        service.raise_for_status()
        service = s.get(f"/api/v1/services/{service_id}", json=True).json()["data"]

    status = True
    domain = ""
    port = ""
    connect_info = format_connection_info(
        protocol=protocol,
        hostname=service["hostname"],
        tcp_hostname=service["tcp_hostname"],
        tcp_port=service["tcp_port"],
    )
    return status, domain, port, connect_info


DEPLOY_HANDLERS = {"ssh": ssh, "registry": registry, "cloud": cloud}
