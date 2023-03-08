import json
import subprocess
import tempfile
from pathlib import Path
from slugify import slugify


def login_registry(host, username, password):
    subprocess.call(["docker", "login", "-u", username, "-p"], password, host)


def build_image(challenge):
    name = slugify(challenge["name"])
    path = Path(challenge.file_path).parent.absolute() / challenge["image"]
    print(f"Building {name} from {path}")
    subprocess.call(["docker", "build", "-t", name, "."], cwd=path)
    print(f"Built {name}")
    return name


def push_image(local_tag, location):
    print(f"Pushing {local_tag} to {location}")
    subprocess.call(["docker", "tag", local_tag, location])
    subprocess.call(["docker", "push", location])


def export_image(challenge):
    name = slugify(challenge["name"])
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{name}.docker.tar")
    subprocess.call(["docker", "save", "--output", temp.name, name])
    return temp.name


def get_exposed_ports(challenge):
    image_name = slugify(challenge["name"])
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
