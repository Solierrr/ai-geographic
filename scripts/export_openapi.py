"""Grava o contrato OpenAPI do serviço em openapi.yaml, a partir do código."""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.api.app import build_openapi

VERSION_MARKER = " # x-release-please-version"


def main() -> None:
    schema = build_openapi(include_internal=True)
    text = yaml.safe_dump(schema, sort_keys=False, allow_unicode=True, width=120)
    version_line = f"  version: {schema['info']['version']}\n"
    text = text.replace(version_line, version_line.rstrip("\n") + VERSION_MARKER + "\n", 1)
    (ROOT / "openapi.yaml").write_text(text, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
