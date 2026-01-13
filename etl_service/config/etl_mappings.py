from pathlib import Path

import yaml
from pydantic import BaseModel


class Mapping(BaseModel):
    postgres_table: str
    es_index: str
    es_index_file: str


CONFIG_PATH = Path(__file__).parent / "etl_mappings.yaml"


def load_mappings(path: Path = CONFIG_PATH) -> list[Mapping]:
    raw = yaml.safe_load(path.read_text())
    return [Mapping(**item) for item in raw]


# Load once and expose
MAPPINGS: list[Mapping] = load_mappings()
