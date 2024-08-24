from ctfcli.core.config import Config
from ctfcli.utils.tools import safe_format


class Media:
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
