import os

from ctfcli.core.config import Config
from ctfcli.core.exceptions import ProjectNotInitialized
from ctfcli.utils.tools import safe_format


class Media:
    @staticmethod
    def upload(api, path, location: str) -> str:
        file_payload = {
            "type": "page",
            "location": location,
        }

        with open(path, mode="rb") as file_handle:
            # Specifically use data= here to send multipart/form-data
            r = api.post("/api/v1/files", files={"file": (os.path.basename(path), file_handle)}, data=file_payload)
            r.raise_for_status()
            resp = r.json()
            return resp["data"][0]["location"]

    @staticmethod
    def replace_placeholders(content: str) -> str:
        config = Config()
        try:
            section = config["media"]
        except KeyError:
            section = []
        for m in section:
            content = safe_format(content, items={m: config["media"][m]})
        return content

    @staticmethod
    def render(text):
        # Substitute [media] placeholders from .ctf/config; no-op if text isn't a
        # string or the project config can't be located (e.g. outside a project).
        if not isinstance(text, str):
            return text

        try:
            return Media.replace_placeholders(text)
        except ProjectNotInitialized:
            return text

    @staticmethod
    def render_hints(hints: list) -> list:
        # Return a copy of the hints list with [media] placeholders rendered in
        # each hint's content, preserving the str-vs-dict structure used by
        # challenge.yml / the normalized challenge.
        rendered = []
        for hint in hints:
            if isinstance(hint, str):
                rendered.append(Media.render(hint))
            elif isinstance(hint, dict) and "content" in hint:
                rendered.append({**hint, "content": Media.render(hint["content"])})
            else:
                rendered.append(hint)

        return rendered
