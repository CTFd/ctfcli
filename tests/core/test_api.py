import unittest
from unittest import mock
from unittest.mock import MagicMock, call

from ctfcli.core.api import API


class MockConfigSection(dict):
    def __init__(self, data):
        super(MockConfigSection, self).__init__(data)

    # this is a wrong implementation but all that's necessary for this test
    def getboolean(self, key, default=None):
        if key not in self:
            return default

        return self[key]


class TestAPI(unittest.TestCase):
    def test_api_object_ensures_trailing_slash_on_prefix_url(self):
        test_urls = [
            "https://example.com/test/",
            "https://example.com/test",
            "https://example.com/test////",
        ]

        for url in test_urls:
            mock_config = {"config": MockConfigSection({"url": url, "access_token": "test"})}

            with mock.patch("ctfcli.core.api.Config", return_value=mock_config):
                api = API()
                self.assertEqual(api.prefix_url, "https://example.com/test/")

    @mock.patch(
        "ctfcli.core.api.Config",
        return_value=MockConfigSection(
            {"config": MockConfigSection({"url": "https://example.com/test", "access_token": "test"})}
        ),
    )
    @mock.patch("ctfcli.core.api.Session.request")
    def test_api_object_request_strips_preceding_slash_from_url_path(self, mock_request: MagicMock, *args, **kwargs):
        api = API()
        api.request("GET", "/path")
        api.request("GET", "path")

        mock_request.assert_has_calls(
            [
                call("GET", "https://example.com/test/path", headers={"Content-Type": "application/json"}),
                call("GET", "https://example.com/test/path", headers={"Content-Type": "application/json"}),
            ]
        )

    @mock.patch(
        "ctfcli.core.api.Config",
        return_value={"config": MockConfigSection({"url": "https://example.com/test", "access_token": "test"})},
    )
    @mock.patch("ctfcli.core.api.Session.request")
    def test_api_object_request_assigns_prefix_url(self, mock_request: MagicMock, *args, **kwargs):
        api = API()
        api.request("GET", "path")
        mock_request.assert_called_once_with(
            "GET", "https://example.com/test/path", headers={"Content-Type": "application/json"}
        )

    def test_api_object_assigns_ssl_verify(self, *args, **kwargs):
        with mock.patch(
            "ctfcli.core.api.Config",
            return_value={
                "config": MockConfigSection(
                    {
                        "url": "https://example.com/test",
                        "access_token": "test",
                    }
                )
            },
        ):
            api = API()
            # expect the default to be true
            self.assertTrue(api.verify)

        with mock.patch(
            "ctfcli.core.api.Config",
            return_value={
                "config": MockConfigSection(
                    {
                        "url": "https://example.com/test",
                        "access_token": "test",
                        "ssl_verify": True,
                    }
                )
            },
        ):
            api = API()
            self.assertTrue(api.verify)

        with mock.patch(
            "ctfcli.core.api.Config",
            return_value={
                "config": MockConfigSection(
                    {
                        "url": "https://example.com/test",
                        "access_token": "test",
                        "ssl_verify": False,
                    }
                )
            },
        ):
            api = API()
            self.assertFalse(api.verify)

    @mock.patch("ctfcli.core.api.Config")
    def test_api_expects_value_error(self, mock_config_constructor: MagicMock):
        mock_config_constructor.return_value = {
            "config": MagicMock(
                getboolean=MagicMock(side_effect=ValueError("Invalid boolean value")),
                get=MagicMock(return_value="/tmp/certificate"),
            )
        }

        api = API()
        self.assertEqual("/tmp/certificate", api.verify)

    @mock.patch(
        "ctfcli.core.api.Config",
        return_value={
            "config": MockConfigSection(
                {
                    "url": "https://example.com/test",
                    "access_token": "test",
                }
            )
        },
    )
    def test_api_object_assigns_headers(self, *args, **kwargs):
        api = API()

        self.assertIn("Authorization", api.headers)
        self.assertEqual("Token test", api.headers["Authorization"])

    @mock.patch(
        "ctfcli.core.api.Config",
        return_value={
            "config": MockConfigSection(
                {
                    "url": "https://example.com/test",
                    "access_token": "test",
                }
            ),
            "cookies": MockConfigSection({"test-cookie": "test-value"}),
        },
    )
    def test_api_object_assigns_cookies(self, *args, **kwargs):
        api = API()
        self.assertIn("test-cookie", api.cookies)
        self.assertEqual(api.cookies["test-cookie"], "test-value")

    @mock.patch(
        "ctfcli.core.api.Config",
        return_value={
            "config": MockConfigSection(
                {
                    "url": "https://example.com/",
                    "access_token": "test",
                }
            ),
        },
    )
    @mock.patch("ctfcli.core.api.Session.request")
    def test_request_does_not_override_form_data_content_type(self, mock_request: MagicMock, *args, **kwargs):
        api = API()
        api.request("GET", "/test", data="some-file")
        mock_request.assert_called_once_with("GET", "https://example.com/test", data="some-file", files=None)
