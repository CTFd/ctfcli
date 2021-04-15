import json
import subprocess
import tempfile
from pathlib import Path


def sanitize_name(name):
    """
    Function to sanitize names to docker safe image names
    TODO: Good enough but probably needs to be more conformant with docker
    """
    return name.lower().replace(" ", "-")


def build_image(challenge):
    name = sanitize_name(challenge["name"])
    path = Path(challenge.file_path).parent.absolute()
    print(f"Building {name} from {path}")
    subprocess.call(["docker", "build", "-t", name, "."], cwd=path)
    return name


def export_image(challenge):
    name = sanitize_name(challenge["name"])
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{name}.docker.tar")
    subprocess.call(["docker", "save", "--output", temp.name, name])
    return temp.name


def get_exposed_ports(challenge):
    image_name = sanitize_name(challenge["name"])
    output = subprocess.check_output(
        ["docker", "inspect", "--format={{json .Config.ExposedPorts }}", image_name,]
    )
    output = json.loads(output)
    if output:
        ports = list(output.keys())
        if ports:
            # Split '2323/tcp'
            port = ports[0]
            port = port.split("/")
            port = port[0]
            return port
        else:
            return None
    else:
        return None
