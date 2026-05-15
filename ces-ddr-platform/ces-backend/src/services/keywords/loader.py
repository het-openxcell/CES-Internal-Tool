import importlib.resources
import json


class KeywordLoader:
    keywords: dict[str, str] = {}

    @classmethod
    def load(cls) -> None:
        data = importlib.resources.files("src.resources").joinpath("keywords.json").read_text()
        cls.keywords = json.loads(data)

    @classmethod
    def get_keywords(cls) -> dict[str, str]:
        return dict(cls.keywords)

    @classmethod
    def reload(cls, new_data: dict[str, str]) -> None:
        cls.keywords = new_data
