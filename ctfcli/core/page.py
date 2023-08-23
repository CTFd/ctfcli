from os import PathLike
from pathlib import Path
from typing import Dict, List, Optional, Union

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

import click
import frontmatter

from ctfcli.core.api import API
from ctfcli.core.config import Config
from ctfcli.core.exceptions import (
    IllegalPageOperation,
    InvalidPageConfiguration,
    InvalidPageFormat,
)

PAGE_FORMATS = {
    ".md": "markdown",
    ".html": "html",
    ".htm": "html",
}


# Note:
# This class cannot delete pages yet - which can lead to expected, but perhaps unintuitive behavior with sync
# When changing a route of a page, it will not be possible to sync it as we will not be able to determine an existing
# page to update (that is done with the route).
# The page can be pushed, but that will just create another page at the new route - which can then be reflected locally
# by using pull. The old page has to be deleted manually or hidden with sync and hidden: true


class Page:
    _remote_pages: Optional[List[Self]] = None
    _remote_page_ids: Optional[Dict[str, int]] = None

    def __init__(self, page_path: Optional[Union[str, PathLike]] = None, page_id: Optional[int] = None):
        # single page object can only be created as either local or remote at the moment
        # this can be changed later to allow a merge-like behavior
        if not page_path and not page_id or page_path and page_id:
            raise InvalidPageConfiguration

        self.api = API()

        if page_id:
            # if page is remote - it can only be used for downloading
            self.page_id = page_id
            page_data = self._get_data_by_id()
            self.format = page_data["format"]

            # if page is remote we have to infer a local file name
            # default to route.ext which also works for nesting: nested/route.ext
            self.page_file_path = f"{page_data['route']}{self.get_format_extension(self.format)}"
        else:
            # if page is local - it can be used for sync, upload and download (with overwrite)
            self.page_path = Path(page_path)
            page_data = self._get_data_by_path()
            self.format = self.get_format(self.page_path.suffix)

            # check if page is also remote, so that we can potentially sync
            remote_page_id = self.get_remote_page_id(page_data["route"])
            if remote_page_id:
                self.page_id = remote_page_id

            # if page is local we can know the page file path
            # which should be output as relative to the pages directory
            self.page_file_path = str(self.page_path.relative_to(Config.get_pages_path()))

        self.route = page_data["route"]
        self.title = page_data["title"]
        self.content = page_data["content"]
        self.is_draft = bool(page_data.get("draft", False))
        self.is_hidden = bool(page_data.get("hidden", False))
        self.is_auth_required = bool(page_data.get("auth_required", False))

    def __str__(self):
        return self.page_file_path

    def _get_data_by_path(self) -> Optional[Dict]:
        if not self.page_path.exists():
            return

        with open(self.page_path, "r") as page_file:
            page_data = frontmatter.load(page_file)

            return {**page_data.metadata, "content": page_data.content}

    def _get_data_by_id(self) -> Optional[Dict]:
        r = self.api.get(f"/api/v1/pages/{self.page_id}")

        if not r.ok:
            return

        return r.json()["data"]

    def as_dict(self):
        return {
            "route": self.route,
            "title": self.title,
            "content": self.content,
            "draft": self.is_draft,
            "hidden": self.is_hidden,
            "auth_required": self.is_auth_required,
            "format": self.format,
        }

    def as_frontmatter_post(self) -> frontmatter.Post:
        metadata = {
            "route": self.route,
            "title": self.title,
            "draft": self.is_draft,
            "hidden": self.is_hidden,
            "auth_required": self.is_auth_required,
        }
        return frontmatter.Post(self.content, **metadata)

    def sync(self):
        # sync / update remote copy with local state
        if not getattr(self, "page_id", None):
            raise IllegalPageOperation(
                f"Cannot sync page '{self.page_file_path}' - remote version does not exists. Use push first."
            )

        if not getattr(self, "page_path", None):
            raise IllegalPageOperation(
                f"Cannot sync page '{self.page_file_path}' - local version does not exists. Use pull first."
            )

        r = self.api.patch(f"/api/v1/pages/{self.page_id}", json=self.as_dict())
        r.raise_for_status()

    def pull(self, overwrite=False):
        # download / create local copy of a remote page
        # download without overwrite is useful only for initial pull
        if not getattr(self, "page_id", None):
            raise IllegalPageOperation(f"Cannot pull page '{self.page_file_path}' - remote version does not exists.")

        page_path = Config.get_pages_path() / self.page_file_path

        # make sure all necessary directories exist
        page_path.parent.mkdir(parents=True, exist_ok=True)

        if page_path.is_file():
            if not overwrite:
                raise IllegalPageOperation(f"Cannot pull page '{self.page_file_path}' - file already exists.")

            click.secho(f"Overwriting page file '{self.page_file_path}'", fg="yellow")

        with open(page_path, "wb+") as page_file:
            frontmatter.dump(self.as_frontmatter_post(), page_file)

    def push(self):
        # upload / create remote copy of a local page
        if getattr(self, "page_id", None):
            raise IllegalPageOperation(
                f"Cannot push page '{self.page_file_path}' - remote version exists. Use sync instead."
            )

        r = self.api.post("/api/v1/pages", json=self.as_dict())
        r.raise_for_status()

        self.page_id = r.json()["data"]["id"]

    @staticmethod
    def get_format(ext) -> str:
        if ext not in PAGE_FORMATS:
            raise InvalidPageFormat

        return PAGE_FORMATS[ext]

    @staticmethod
    def get_format_extension(fmt) -> str:
        for supported_ext, supported_fmt in PAGE_FORMATS.items():
            if fmt == supported_fmt:
                return supported_ext

        raise InvalidPageFormat

    @classmethod
    def get_remote_pages(cls) -> List[Self]:
        # if we find a saved list of remote pages we can use it
        if cls._remote_pages:
            return cls._remote_pages

        api = API()
        installed_pages = api.get("/api/v1/pages").json()["data"]

        pages = []
        for page in installed_pages:
            pages.append(Page(page_id=page["id"]))

        # save remote pages for reuse
        cls._remote_pages = pages
        return pages

    @classmethod
    def get_remote_page_id(cls, route: str) -> Optional[int]:
        # if we find a saved cache, and the route has a page_id associated - we can return it
        if cls._remote_page_ids and route in cls._remote_page_ids:
            return cls._remote_page_ids[route]

        # if we find a saved list of remote pages instead, we can also use it
        if cls._remote_pages:
            for page in cls._remote_pages:
                if route == page.route:
                    return page.page_id

        # otherwise we just take the result of listing all pages to search for the id
        # and build the lookup cache for further use
        api = API()
        remote_pages = api.get("/api/v1/pages").json()["data"]

        remote_page_ids = {}
        for page in remote_pages:
            remote_page_ids[page["route"]] = page["id"]

        cls._remote_page_ids = remote_page_ids

        # finally return the page id from the lookup dict, if the route has been found
        return cls._remote_page_ids.get(route, None)

    @classmethod
    def get_local_pages(cls) -> List[Self]:
        config = Config()
        pages_dir = config.get_pages_path()

        page_files = []
        for supported_ext in PAGE_FORMATS.keys():
            page_files.extend(list(pages_dir.glob(f"**/*{supported_ext}")))

        pages = []
        for page_path in page_files:
            pages.append(Page(page_path=page_path))

        return pages
