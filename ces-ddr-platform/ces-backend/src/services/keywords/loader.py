import importlib.resources
import json


class KeywordLoader:
    _keywords: dict[str, str] = {}

    @classmethod
    def load(cls) -> None:
        data = importlib.resources.files("src.resources").joinpath("keywords.json").read_text()
        cls._keywords = json.loads(data)

    @classmethod
    def get_keywords(cls) -> dict[str, str]:
        return dict(cls._keywords)

    @classmethod
    def reload(cls, new_data: dict[str, str]) -> None:
        cls._keywords = new_data
