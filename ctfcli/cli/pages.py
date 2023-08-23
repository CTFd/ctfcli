import logging
from typing import Optional

import click

from ctfcli.core.exceptions import PageException
from ctfcli.core.page import Page

log = logging.getLogger("ctfcli.cli.pages")


class PagesCommand:
    # _page_operation is a wrapper to calling Page methods, to avoid code duplication, it will:
    # - log the operation
    # - perform it on the page object, with given arguments
    # - handle the possible exception and echo it out with click
    # - return right exit code
    def _page_operation(self, page: Page, operation: str, *args, **kwargs) -> int:
        if operation not in ["push", "pull", "sync"]:
            raise ValueError

        page_operation = getattr(page, operation)
        try:
            log.debug(f"{operation}: {page}")
            page_operation(*args, **kwargs)
            click.secho(f"Successfully {operation}ed page '{page.page_file_path}'", fg="green")
            return 0
        except PageException as e:
            click.secho(str(e), fg="red")
            return 1

    def push(self, page: Optional[str] = None) -> int:
        pages = Page.get_local_pages()

        if page:
            page_object = next(
                (page_obj for page_obj in pages if page == page_obj.page_file_path),
                None,
            )
            if page_object:
                return self._page_operation(page_object, "push")

            click.secho(f"Could not find page '{page}'", fg="red")
            return 1

        return_code = 0
        for page_object in pages:
            status = self._page_operation(page_object, "push")

            if status == 1:
                return_code = 1

        return return_code

    def sync(self, page: Optional[str] = None) -> int:
        pages = Page.get_local_pages()

        if page:
            page_object = next(
                (page_obj for page_obj in pages if page == page_obj.page_file_path),
                None,
            )
            if page_object:
                return self._page_operation(page_object, "sync")

            click.secho(f"Could not find page '{page}'", fg="red")
            return 1

        return_code = 0
        for page_object in pages:
            status = self._page_operation(page_object, "sync")

            if status == 1:
                return_code = 1

        return return_code

    def pull(self, route: Optional[str] = None, force=False) -> int:
        if route:
            page_id = Page.get_remote_page_id(route)
            if not page_id:
                click.secho(f"Could not find page with route '{route}'", fg="red")
                return 1

            page_object = Page(page_id=page_id)
            return self._page_operation(page_object, "pull", overwrite=force)

        return_code = 0
        pages = Page.get_remote_pages()
        for page_object in pages:
            status = self._page_operation(page_object, "pull", overwrite=force)
            if status == 1:
                return_code = 1

        return return_code
