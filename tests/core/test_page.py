import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, call

import frontmatter

from ctfcli.core.exceptions import (
    IllegalPageOperation,
    InvalidPageConfiguration,
    InvalidPageFormat,
)
from ctfcli.core.page import Page

BASE_DIR = Path(__file__).parent.parent


class TestPage(unittest.TestCase):
    # use a test challenge path as cwd to avoid mocking config
    minimal_challenge_cwd = BASE_DIR / "fixtures" / "challenges" / "test-challenge-minimal"

    def tearDown(self) -> None:
        # reset class cache after each test
        Page._remote_pages = None
        Page._remote_page_ids = None

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_loads_local_markdown_page(self, *args, **kwargs):
        page_path = BASE_DIR / "fixtures" / "challenges" / "pages" / "markdown-page.md"
        page = Page(page_path=page_path)

        self.assertEqual("markdown-page", page.route)
        self.assertEqual("Markdown Page", page.title)
        self.assertEqual("# Hello World!", page.content)
        self.assertEqual("markdown", page.format)
        self.assertTrue(page.is_draft)
        self.assertTrue(page.is_hidden)
        self.assertTrue(page.is_auth_required)

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_loads_local_html_page(self, *args, **kwargs):
        page_path = BASE_DIR / "fixtures" / "challenges" / "pages" / "html-page.html"
        page = Page(page_path=page_path)

        self.assertEqual("html-page", page.route)
        self.assertEqual("HTML Page", page.title)
        self.assertEqual("<h1>Hello World!</h1>", page.content)
        self.assertEqual("html", page.format)
        self.assertFalse(page.is_draft)
        self.assertFalse(page.is_hidden)
        self.assertFalse(page.is_auth_required)

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_loads_remote_markdown_page(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value

        mock_api.get.return_value.json.return_value = {
            "success": True,
            "data": {
                "format": "markdown",
                "files": [],
                "draft": True,
                "title": "Markdown Page",
                "id": 1,
                "content": "# Hello World!",
                "auth_required": True,
                "hidden": True,
                "route": "markdown-page",
            },
        }

        page = Page(page_id=1)

        self.assertEqual("markdown-page", page.route)
        self.assertEqual("Markdown Page", page.title)
        self.assertEqual("# Hello World!", page.content)
        self.assertEqual("markdown", page.format)
        self.assertTrue(page.is_draft)
        self.assertTrue(page.is_hidden)
        self.assertTrue(page.is_auth_required)

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_loads_remote_html_page(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value

        mock_api.get.return_value.json.return_value = {
            "success": True,
            "data": {
                "format": "html",
                "files": [],
                "draft": False,
                "title": "HTML Page",
                "id": 1,
                "content": "<h1>Hello World!</h1>",
                "auth_required": False,
                "hidden": False,
                "route": "html-page",
            },
        }

        page = Page(page_id=1)

        self.assertEqual("html-page", page.route)
        self.assertEqual("HTML Page", page.title)
        self.assertEqual("<h1>Hello World!</h1>", page.content)
        self.assertEqual("html", page.format)
        self.assertFalse(page.is_draft)
        self.assertFalse(page.is_hidden)
        self.assertFalse(page.is_auth_required)

    def test_raises_if_no_path_or_id_provided(self):
        with self.assertRaises(InvalidPageConfiguration):
            Page(
                page_id=1,
                page_path=BASE_DIR / "fixtures" / "challenges" / "pages" / "html-page.html",
            )

    def test_raises_if_both_path_and_id_provided(self):
        with self.assertRaises(InvalidPageConfiguration):
            Page()

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_as_dict(self, *args, **kwargs):
        page_path = BASE_DIR / "fixtures" / "challenges" / "pages" / "markdown-page.md"
        page = Page(page_path=page_path)

        expected_dict = {
            "route": "markdown-page",
            "title": "Markdown Page",
            "content": "# Hello World!",
            "format": "markdown",
            "draft": True,
            "hidden": True,
            "auth_required": True,
        }

        self.assertDictEqual(expected_dict, page.as_dict())

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_as_frontmatter_post(self, *args, **kwargs):
        page_path = BASE_DIR / "fixtures" / "challenges" / "pages" / "markdown-page.md"
        page = Page(page_path=page_path)

        expected_metadata = {
            "route": "markdown-page",
            "title": "Markdown Page",
            "draft": True,
            "hidden": True,
            "auth_required": True,
        }

        page_as_post = page.as_frontmatter_post()
        self.assertIsInstance(page_as_post, frontmatter.Post)
        self.assertEqual(page_as_post.content, "# Hello World!")
        self.assertDictEqual(page_as_post.metadata, expected_metadata)

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_syncs_local_page(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value

        mock_page_data = {
            "format": "html",
            "files": [],
            "draft": False,
            "title": "HTML Page",
            "id": 1,
            "content": "<h1>Hello World!</h1>",
            "auth_required": False,
            "hidden": False,
            "route": "html-page",
        }

        mock_api.get.return_value.json.side_effect = [
            # mock first call to /api/v1/pages
            {"success": True, "data": [mock_page_data]},
            # mock second call to /api/v1/pages/1
            {"success": True, "data": mock_page_data},
        ]

        mock_api.post.return_value.json.return_value = {
            "success": True,
            "data": mock_page_data,
        }

        page_path = BASE_DIR / "fixtures" / "challenges" / "pages" / "html-page.html"
        page = Page(page_path=page_path)
        page.sync()

        expected_page_payload = {
            "format": "html",
            "draft": False,
            "title": "HTML Page",
            "content": "<h1>Hello World!</h1>",
            "auth_required": False,
            "hidden": False,
            "route": "html-page",
        }

        mock_api.patch.assert_called_once_with("/api/v1/pages/1", json=expected_page_payload)

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_cannot_sync_local_page_if_it_does_not_exist(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value

        mock_page_data = {
            "format": "html",
            "files": [],
            "draft": False,
            "title": "HTML Page",
            "id": 1,
            "content": "<h1>Hello World!</h1>",
            "auth_required": False,
            "hidden": False,
            "route": "html-page",
        }

        # mock call to /api/v1/page/1
        mock_api.get.return_value.json.return_value = {
            "success": True,
            "data": mock_page_data,
        }

        page = Page(page_id=1)

        with self.assertRaises(IllegalPageOperation) as e:
            page.sync()

        self.assertEqual(
            "Cannot sync page 'html-page.html' - local version does not exists. Use pull first.", str(e.exception)
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_cannot_sync_local_page_if_remote_does_not_exist(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value

        # mock call to /api/v1/pages
        mock_api.get.return_value.json.return_value = {"success": True, "data": []}

        page_path = BASE_DIR / "fixtures" / "challenges" / "pages" / "html-page.html"
        page = Page(page_path=page_path)

        with self.assertRaises(IllegalPageOperation) as e:
            page.sync()

        self.assertEqual(
            "Cannot sync page 'html-page.html' - remote version does not exists. Use push first.", str(e.exception)
        )

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_downloads_remote_page(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value

        mock_api.get.return_value.json.return_value = {
            "success": True,
            "data": {
                "format": "html",
                "files": [],
                "draft": False,
                "title": "Test Page",
                "id": 1,
                "content": "<h1>Hello World!</h1>",
                "auth_required": False,
                "hidden": False,
                "route": "test-page",
            },
        }

        page = Page(page_id=1)
        page.pull()

        expected_path = BASE_DIR / "fixtures" / "challenges" / "pages" / "test-page.html"
        self.assertTrue(expected_path.exists())

        expected_path.unlink()

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_downloads_remote_nested_page(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value

        mock_api.get.return_value.json.return_value = {
            "success": True,
            "data": {
                "format": "html",
                "files": [],
                "draft": False,
                "title": "Test Page",
                "id": 1,
                "content": "<h1>Hello World!</h1>",
                "auth_required": False,
                "hidden": False,
                "route": "test/test-page",
            },
        }

        page = Page(page_id=1)
        page.pull()

        expected_path = BASE_DIR / "fixtures" / "challenges" / "pages" / "test" / "test-page.html"
        self.assertTrue(expected_path.exists())

        expected_path.unlink()
        expected_path.parent.rmdir()

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_cannot_download_remote_page_if_file_exists(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value

        mock_page_data = {
            "format": "html",
            "files": [],
            "draft": False,
            "title": "HTML Page",
            "id": 1,
            "content": "<h1>Hello World!</h1>",
            "auth_required": False,
            "hidden": False,
            "route": "html-page",
        }

        mock_api.get.return_value.json.return_value = {
            "success": True,
            "data": mock_page_data,
        }

        page = Page(page_id=1)
        with self.assertRaises(IllegalPageOperation) as e:
            page.pull()

        self.assertEqual("Cannot pull page 'html-page.html' - file already exists.", str(e.exception))

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.click.secho")
    @mock.patch("ctfcli.core.page.API")
    def test_downloads_remote_page_with_overwrite(
        self, mock_api_constructor: MagicMock, mock_secho: MagicMock, *args, **kwargs
    ):
        mock_api = mock_api_constructor.return_value

        mock_api.get.return_value.json.return_value = {
            "success": True,
            "data": {
                "format": "html",
                "files": [],
                "draft": False,
                "title": "HTML Page",
                "id": 1,
                "content": "<h1>Hello World!</h1>",
                "auth_required": False,
                "hidden": False,
                "route": "html-page",
            },
        }

        page = Page(page_id=1)
        page.pull(overwrite=True)

        mock_secho.assert_called_once_with("Overwriting page file 'html-page.html'", fg="yellow")

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_cannot_download_remote_page_if_it_does_not_exist(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value
        mock_api.get.return_value.json.return_value = {"success": True, "data": []}

        page_path = BASE_DIR / "fixtures" / "challenges" / "pages" / "html-page.html"
        page = Page(page_path=page_path)

        with self.assertRaises(IllegalPageOperation) as e:
            page.pull()

        self.assertEqual("Cannot pull page 'html-page.html' - remote version does not exists.", str(e.exception))

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_uploads_local_page(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value

        page_path = BASE_DIR / "fixtures" / "challenges" / "pages" / "html-page.html"
        page = Page(page_path=page_path)
        page.push()

        expected_page_payload = {
            "route": "html-page",
            "title": "HTML Page",
            "content": "<h1>Hello World!</h1>",
            "draft": False,
            "hidden": False,
            "auth_required": False,
            "format": "html",
        }

        mock_api.post.assert_called_once_with("/api/v1/pages", json=expected_page_payload)

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_cannot_upload_local_page_if_remote_exists(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value

        mock_page_data = {
            "format": "html",
            "files": [],
            "draft": False,
            "title": "HTML Page",
            "id": 1,
            "content": "<h1>Hello World!</h1>",
            "auth_required": False,
            "hidden": False,
            "route": "html-page",
        }

        mock_api.get.return_value.json.side_effect = [
            # 1st call to /api/v1/pages
            {"success": True, "data": [mock_page_data]},
            # 2nd call to /api/v1/pages/1
            {"success": True, "data": mock_page_data},
        ]

        page_path = BASE_DIR / "fixtures" / "challenges" / "pages" / "html-page.html"
        page = Page(page_path=page_path)

        with self.assertRaises(IllegalPageOperation) as e:
            page.push()

        self.assertEqual(
            "Cannot push page 'html-page.html' - remote version exists. Use sync instead.", str(e.exception)
        )

    def test_get_format(self):
        formats = {
            ".md": "markdown",
            ".html": "html",
            ".htm": "html",
        }

        for ext, fmt in formats.items():
            self.assertEqual(fmt, Page.get_format(ext))

    def test_get_format_extension(self):
        extensions = {"markdown": [".md"], "html": [".html", ".htm"]}

        for fmt, allowed_ext in extensions.items():
            self.assertIn(Page.get_format_extension(fmt), allowed_ext)

    def test_get_format_raises_on_unknown_format(self):
        with self.assertRaises(InvalidPageFormat):
            Page.get_format(".rst")

    def test_get_format_extension_raises_on_unknown_format(self):
        with self.assertRaises(InvalidPageFormat):
            Page.get_format("restructured-text")


class TestPageLoading(unittest.TestCase):
    minimal_challenge_cwd = BASE_DIR / "fixtures" / "challenges" / "test-challenge-minimal"

    def tearDown(self) -> None:
        # reset class cache after each test
        Page._remote_pages = None
        Page._remote_page_ids = None

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_get_local_pages(self, *args, **kwargs):
        local_pages = Page.get_local_pages()

        # expect all pages to be of type Page, and expect to find all the titles
        expected_page_titles = ["Nested HTML Page", "HTML Page", "Markdown Page"]
        for page in local_pages:
            expected_page_titles.pop(expected_page_titles.index(page.title))
            self.assertIsInstance(page, Page)

        self.assertEqual(3, len(local_pages))
        self.assertEqual(0, len(expected_page_titles))

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_get_remote_pages(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value
        mock_api.get.return_value.json.side_effect = [
            {  # 1st request - to /api/v1/pages
                "success": True,
                "data": [
                    {
                        "format": "markdown",
                        "files": [],
                        "draft": True,
                        "title": "Markdown Page",
                        "id": 1,
                        "auth_required": True,
                        "hidden": True,
                        "route": "markdown-page",
                    },
                    {
                        "format": "html",
                        "files": [],
                        "draft": False,
                        "title": "HTML Page",
                        "id": 2,
                        "auth_required": False,
                        "hidden": False,
                        "route": "html-page",
                    },
                    {
                        "format": "html",
                        "files": [],
                        "draft": False,
                        "title": "Nested HTML Page",
                        "id": 3,
                        "auth_required": False,
                        "hidden": False,
                        "route": "nested-html-page",
                    },
                ],
            },
            # subsequent request to fetch pages individually
            {
                "success": True,
                "data": {
                    "format": "markdown",
                    "files": [],
                    "draft": True,
                    "title": "Markdown Page",
                    "id": 1,
                    "content": "# Hello World!",
                    "auth_required": True,
                    "hidden": True,
                    "route": "markdown-page",
                },
            },
            {
                "success": True,
                "data": {
                    "format": "html",
                    "files": [],
                    "draft": False,
                    "title": "HTML Page",
                    "id": 2,
                    "content": "<h1>Hello World!</h1>",
                    "auth_required": False,
                    "hidden": False,
                    "route": "html-page",
                },
            },
            {
                "success": True,
                "data": {
                    "format": "html",
                    "files": [],
                    "draft": False,
                    "title": "Nested HTML Page",
                    "id": 3,
                    "content": "<h1>Hello Nested!</h1>",
                    "auth_required": False,
                    "hidden": False,
                    "route": "nested-html-page",
                },
            },
        ]

        remote_pages = Page.get_remote_pages()

        # expect all pages to be of type Page, and expect to find all the titles
        expected_page_titles = ["Nested HTML Page", "HTML Page", "Markdown Page"]
        for page in remote_pages:
            expected_page_titles.pop(expected_page_titles.index(page.title))
            self.assertIsInstance(page, Page)

        self.assertEqual(3, len(remote_pages))
        self.assertEqual(0, len(expected_page_titles))

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_get_remote_page_id(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value
        mock_api.get.return_value.json.return_value = {
            "success": True,
            "data": [
                {
                    "format": "markdown",
                    "files": [],
                    "draft": True,
                    "title": "Markdown Page",
                    "id": 1,
                    "auth_required": True,
                    "hidden": True,
                    "route": "markdown-page",
                },
                {
                    "format": "html",
                    "files": [],
                    "draft": False,
                    "title": "HTML Page",
                    "id": 2,
                    "auth_required": False,
                    "hidden": False,
                    "route": "html-page",
                },
                {
                    "format": "html",
                    "files": [],
                    "draft": False,
                    "title": "Nested HTML Page",
                    "id": 3,
                    "auth_required": False,
                    "hidden": False,
                    "route": "nested-html-page",
                },
            ],
        }

        page_id = Page.get_remote_page_id("nested-html-page")
        self.assertEqual(3, page_id)

        mock_api.get.assert_called_once_with("/api/v1/pages")

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_get_remote_page_id_saves_found_id(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value
        mock_api.get.return_value.json.return_value = {
            "success": True,
            "data": [
                {
                    "format": "markdown",
                    "files": [],
                    "draft": True,
                    "title": "Markdown Page",
                    "id": 1,
                    "auth_required": True,
                    "hidden": True,
                    "route": "markdown-page",
                },
                {
                    "format": "html",
                    "files": [],
                    "draft": False,
                    "title": "HTML Page",
                    "id": 2,
                    "auth_required": False,
                    "hidden": False,
                    "route": "html-page",
                },
            ],
        }

        markdown_page_id = Page.get_remote_page_id("markdown-page")
        self.assertEqual(1, markdown_page_id)

        # expect _remote_pages to be None, as we didn't fetch any full pages - only ids
        self.assertIsNone(Page._remote_pages)

        # expect to find all available page ids in the cache
        self.assertDictEqual(Page._remote_page_ids, {"markdown-page": 1, "html-page": 2})

        html_page_id = Page.get_remote_page_id("html-page")
        self.assertEqual(2, html_page_id)

        # expect to have only made one call
        self.assertEqual(1, mock_api.get.mock_calls.count(call("/api/v1/pages")))

    @mock.patch("ctfcli.core.config.Path.cwd", return_value=minimal_challenge_cwd)
    @mock.patch("ctfcli.core.page.API")
    def test_get_remote_pages_saves_pages(self, mock_api_constructor: MagicMock, *args, **kwargs):
        mock_api = mock_api_constructor.return_value
        mock_api.get.return_value.json.side_effect = [
            {  # 1st request - to /api/v1/pages
                "success": True,
                "data": [
                    {
                        "format": "markdown",
                        "files": [],
                        "draft": True,
                        "title": "Markdown Page",
                        "id": 1,
                        "auth_required": True,
                        "hidden": True,
                        "route": "markdown-page",
                    },
                    {
                        "format": "html",
                        "files": [],
                        "draft": False,
                        "title": "HTML Page",
                        "id": 2,
                        "auth_required": False,
                        "hidden": False,
                        "route": "html-page",
                    },
                    {
                        "format": "html",
                        "files": [],
                        "draft": False,
                        "title": "Nested HTML Page",
                        "id": 3,
                        "auth_required": False,
                        "hidden": False,
                        "route": "nested-html-page",
                    },
                ],
            },
            # subsequent request to fetch pages individually
            {
                "success": True,
                "data": {
                    "format": "markdown",
                    "files": [],
                    "draft": True,
                    "title": "Markdown Page",
                    "id": 1,
                    "content": "# Hello World!",
                    "auth_required": True,
                    "hidden": True,
                    "route": "markdown-page",
                },
            },
            {
                "success": True,
                "data": {
                    "format": "html",
                    "files": [],
                    "draft": False,
                    "title": "HTML Page",
                    "id": 2,
                    "content": "<h1>Hello World!</h1>",
                    "auth_required": False,
                    "hidden": False,
                    "route": "html-page",
                },
            },
            {
                "success": True,
                "data": {
                    "format": "html",
                    "files": [],
                    "draft": False,
                    "title": "Nested HTML Page",
                    "id": 3,
                    "content": "<h1>Hello Nested!</h1>",
                    "auth_required": False,
                    "hidden": False,
                    "route": "nested-html-page",
                },
            },
        ]

        remote_pages = Page.get_remote_pages()

        self.assertEqual(3, len(remote_pages))
        # expect to have saved 3 pages
        self.assertEqual(3, len(Page._remote_pages))

        Page.get_remote_page_id("markdown-page")

        # check that /api/v1/pages has only been called once, even though we requested the id for a page
        self.assertEqual(1, mock_api.get.mock_calls.count(call("/api/v1/pages")))
