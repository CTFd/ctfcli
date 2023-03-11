from .config import generate_session

FORMATS = {
    ".md": "markdown",
    ".html": "html",
    ".htm": "html",
}


def get_current_pages():
    s = generate_session()
    return s.get("/api/v1/pages", json=True).json()["data"]


def get_existing_page(route, pageset=None):
    if pageset is None:
        pageset = get_current_pages()
    for page in pageset:
        if route == page["route"]:
            return page
    return None


def get_format(ext):
    return FORMATS[ext]


def sync_page(matter, path_obj, page_id):
    route = matter["route"]
    title = matter["title"]
    content = matter.content
    draft = bool(matter.get("draft"))
    hidden = bool(matter.get("hidden"))
    auth_required = bool(matter.get("auth_required"))
    format = get_format(path_obj.suffix)

    s = generate_session()
    data = {
        "route": route,
        "title": title,
        "content": content,
        "draft": draft,
        "hidden": hidden,
        "auth_required": auth_required,
        "format": format,
    }
    r = s.patch(f"/api/v1/pages/{page_id}", json=data)
    r.raise_for_status()


def install_page(matter, path_obj):
    route = matter["route"]
    title = matter["title"]
    content = matter.content
    draft = bool(matter.get("draft"))
    hidden = bool(matter.get("hidden"))
    auth_required = bool(matter.get("auth_required"))
    format = get_format(path_obj.suffix)

    s = generate_session()
    data = {
        "route": route,
        "title": title,
        "content": content,
        "draft": draft,
        "hidden": hidden,
        "auth_required": auth_required,
        "format": format,
    }
    r = s.post("/api/v1/pages", json=data)
    r.raise_for_status()
