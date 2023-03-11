import sys
from pathlib import Path
import frontmatter

import click

from ctfcli.utils.config import load_config
from ctfcli.utils.pages import (
    get_current_pages,
    get_existing_page,
    sync_page,
    install_page,
)


class Pages(object):
    def install(self):
        try:
            _config = load_config()
        except Exception as e:
            print(e)
            click.secho("No ctfcli configuration found", fg="red")
            sys.exit(1)

        pages = Path("./pages")
        if pages.is_dir() is False:
            click.secho(
                '"pages" folder not found. All pages must exist in the "pages" folder.',
                fg="red",
            )
            sys.exit(1)
        else:
            current_pages = get_current_pages()

            pagefiles = list(pages.glob("**/*.md")) + list(pages.glob("**/*.html"))
            for path_obj in pagefiles:
                page = frontmatter.load(path_obj)
                existing_page = get_existing_page(
                    route=page["route"], pageset=current_pages
                )

                if existing_page:
                    sync_page(page, path_obj, existing_page["id"])
                else:
                    install_page(page, path_obj)
