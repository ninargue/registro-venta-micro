"""Exporta la especificación OpenAPI de FastAPI a un archivo JSON estático en docs/openapi.json."""

import json
from pathlib import Path

from app.main import app


def export_openapi() -> Path:
    # Ruta canónica hacia docs/openapi.json en la raíz del repositorio
    repo_root = Path(__file__).resolve().parents[3]
    output_path = repo_root / "docs" / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    openapi_schema = app.openapi()
    output_path.write_text(
        json.dumps(openapi_schema, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"OpenAPI schema exported successfully to {output_path}")
    return output_path


if __name__ == "__main__":
    export_openapi()
