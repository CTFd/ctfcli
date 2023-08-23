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

        # Handle cookies section in config
        if "cookies" in config:
            self.cookies.update(dict(config["cookies"]))

    def request(self, method, url, *args, **kwargs):
        # Strip out the preceding / so that urljoin creates the right url
        # considering the appended / on the prefix_url
        url = urljoin(self.prefix_url, url.lstrip("/"))

        # if data= is present, do not modify the content-type
        if kwargs.get("data", None) is not None:
            return super(API, self).request(method, url, *args, **kwargs)

        # otherwise set the content-type to application/json for all API requests
        # modify the headers here instead of using self.headers because we don't want to
        # override the multipart/form-data case above
        if kwargs.get("headers", None) is None:
            kwargs["headers"] = {}

        kwargs["headers"]["Content-Type"] = "application/json"
        return super(API, self).request(method, url, *args, **kwargs)
