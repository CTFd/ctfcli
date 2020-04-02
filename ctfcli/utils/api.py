from urllib.parse import urljoin

from requests import Session


class APISession(Session):
    def __init__(self, prefix_url=None, *args, **kwargs):
        super(APISession, self).__init__(*args, **kwargs)
        self.prefix_url = prefix_url

    def request(self, method, url, *args, **kwargs):
        url = urljoin(self.prefix_url, url)
        return super(APISession, self).request(method, url, *args, **kwargs)
