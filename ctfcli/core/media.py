from ctfcli.core.config import Config
from ctfcli.utils.tools import safe_format


class Media:
    @staticmethod
    def replace_placeholders(content: str) -> str:
        config = Config()
        for m in config["media"]:
            content = safe_format(content, items={m: config["media"][m]})
        return content
