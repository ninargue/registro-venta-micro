"""Exporta y valida la especificación OpenAPI de FastAPI contra docs/api/openapi.json."""

import argparse
import difflib
import json
import sys
import tempfile
from pathlib import Path

from app.main import app


def get_default_openapi_path() -> Path:
    """Retorna la ruta canónica hacia docs/api/openapi.json en la raíz del repositorio."""
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "docs" / "api" / "openapi.json"


def _render_openapi_json() -> str:
    openapi_schema = app.openapi()
    return json.dumps(openapi_schema, indent=2, ensure_ascii=False) + "\n"


def export_openapi(output_path: Path | None = None) -> Path:
    """Genera y escribe el esquema OpenAPI en disco con saltos de línea LF."""
    target_path = output_path or get_default_openapi_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(_render_openapi_json().encode("utf-8"))
    print(f"OpenAPI schema exported successfully to {target_path}")
    return target_path


def check_openapi(expected_path: Path | None = None) -> int:
    """Regenera el esquema en un directorio temporal y lo compara sin modificar el versionado."""
    target_path = expected_path or get_default_openapi_path()
    if not target_path.exists():
        print(
            f"ERROR: No existe el contrato versionado en {target_path}. "
            "Ejecuta: uv run --directory backend python -m app.scripts.export_openapi",
            file=sys.stderr,
        )
        return 1

    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_path = Path(tmp_dir) / "openapi.json"
        temp_path.write_bytes(_render_openapi_json().encode("utf-8"))
        generated = temp_path.read_text(encoding="utf-8")

    versioned = target_path.read_text(encoding="utf-8")

    if generated == versioned:
        print(f"OK: {target_path} coincide con el esquema OpenAPI actual de FastAPI.")
        return 0

    diff_lines = list(
        difflib.unified_diff(
            versioned.splitlines(),
            generated.splitlines(),
            fromfile=f"{target_path} (versionado)",
            tofile="openapi.json (generado)",
            lineterm="",
            n=2,
        )
    )
    max_lines = 40
    preview = "\n".join(diff_lines[:max_lines])
    truncated = (
        f"\n... ({len(diff_lines) - max_lines} líneas más)" if len(diff_lines) > max_lines else ""
    )

    print(
        f"ERROR: {target_path} está desactualizado respecto al código actual.\n"
        "Regenera el contrato con: "
        "uv run --directory backend python -m app.scripts.export_openapi\n"
        f"{preview}{truncated}",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Genera o verifica docs/api/openapi.json")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compara en un archivo temporal sin modificar el contrato versionado.",
    )
    args = parser.parse_args(argv)
    if args.check:
        return check_openapi()
    export_openapi()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
