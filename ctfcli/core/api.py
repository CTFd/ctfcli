from typing import Mapping
from urllib.parse import urljoin

from requests import Session
from requests_toolbelt.multipart.encoder import MultipartEncoder

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

    def request(self, method, url, data=None, files=None, *args, **kwargs):
        # Strip out the preceding / so that urljoin creates the right url
        # considering the appended / on the prefix_url
        url = urljoin(self.prefix_url, url.lstrip("/"))

        # If data or files are any kind of key/value iterable
        # then encode the body as form-data
        if isinstance(data, (list, tuple, Mapping)) or isinstance(files, (list, tuple, Mapping)):
            # In order to use the MultipartEncoder, we need to convert data and files to the following structure :
            # A list of tuple containing the key and the values : List[Tuple[str, str]]
            # For files, the structure can be List[Tuple[str, Tuple[str, str, Optional[str]]]]
            # Example: [ ('file', ('doc.pdf', open('doc.pdf'), 'text/plain') ) ]

            fields = list()
            if isinstance(data, dict):
                # int are not allowed as value in MultipartEncoder
                fields = list(map(lambda v: (v[0], str(v[1]) if isinstance(v[1], int) else v[1]), data.items()))

            if files is not None:
                if isinstance(files, dict):
                    files = list(files.items())
                fields.extend(files)  # type: ignore

            multipart = MultipartEncoder(fields)

            return super(API, self).request(
                method,
                url,
                data=multipart,
                headers={"Content-Type": multipart.content_type},
                *args,
                **kwargs,
            )

        # otherwise set the content-type to application/json for all API requests
        # modify the headers here instead of using self.headers because we don't want to
        # override the multipart/form-data case above
        if data is None and files is None:
            if kwargs.get("headers", None) is None:
                kwargs["headers"] = {}
            kwargs["headers"]["Content-Type"] = "application/json"

        return super(API, self).request(
            method,
            url,
            data=data,
            files=files,
            *args,
            **kwargs,
        )
