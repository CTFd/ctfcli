from urllib.parse import urljoin

from requests import Session

from ctfcli.core.config import Config


class API(Session):
    def __init__(self):
        config = Config()

        # Load required configuration values
        self.url = config["config"]["url"]
        self.access_token = config["config"]["access_token"]

        # Handle SSL verification disabling
        try:
            # Get an ssl_verify config. Default to True if it doesn't exist
            ssl_verify = config["config"].getboolean("ssl_verify", True)
        except ValueError:
            # If we didn't a proper boolean value we should load it as a string
            # https://requests.kennethreitz.org/en/master/user/advanced/#ssl-cert-verification
            ssl_verify = config["config"].get("ssl_verify")

        super(API, self).__init__()

        # Strip out ending slashes and append a singular one, so we generate
        # clean base URLs for both main deployments and subdir deployments
        self.prefix_url = self.url.rstrip("/") + "/"

        # Handle SSL verification
        self.verify = ssl_verify

        # Handle Authorization
        self.headers.update({"Authorization": f"Token {self.access_token}"})

        # Default to application/json for all API requests
        self.headers.update({"Content-Type": "application/json"})

        # Handle cookies section in config
        if "cookies" in config:
            self.cookies.update(dict(config["cookies"]))

    def request(self, method, url, *args, **kwargs):
        # Strip out the preceding / so that urljoin creates the right url
        # considering the appended / on the prefix_url
        url = urljoin(self.prefix_url, url.lstrip("/"))

        kwargs_copy = {**kwargs}

        # if data kwarg is utilized, then files are transferred, we need to set the Content-Type to multipart/form-data
        # (otherwise Content-Type will be application/json as set in the API constructor)
        if kwargs_copy.get("data", None) is not None:
            if kwargs_copy.get("headers", None) is None:
                kwargs_copy["headers"] = {}

            kwargs_copy["headers"]["Content-Type"] = "multipart/form-data"

        return super(API, self).request(method, url, *args, **kwargs_copy)
