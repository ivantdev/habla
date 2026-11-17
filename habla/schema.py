"""Genera el esquema de contrato compartido desde los DTO de FastAPI."""

import json
from pathlib import Path

from pydantic.json_schema import models_json_schema

from .contracts import CONTRACT_MODELS


SCHEMA_PATH = Path(__file__).resolve().parent.parent / "contracts" / "v1.json"


def schema_text() -> str:
    _, schema = models_json_schema([(model, "validation") for model in CONTRACT_MODELS])
    return json.dumps({
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://habla.local/contracts/v1.json",
        **schema,
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    SCHEMA_PATH.parent.mkdir(exist_ok=True)
    SCHEMA_PATH.write_text(schema_text(), encoding="utf-8")
