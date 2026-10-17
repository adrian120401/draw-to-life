"""Entrada local: python app.py; preparación: python -m draw_to_life.models."""

import logging
import os
import argparse

from draw_to_life.config import ROOT, Settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Draw to Life")
    parser.add_argument("--lan", action="store_true", help="Permitir acceso desde la misma red Wi-Fi")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s · %(name)s · %(message)s")
    settings = Settings.from_env()
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    # Cache temporal controlada y sin acceso a directorios ajenos al proyecto.
    os.environ.setdefault("GRADIO_TEMP_DIR", str(ROOT / ".gradio"))
    from draw_to_life.ui import build_ui
    build_ui(settings).launch(
        server_name="0.0.0.0" if args.lan else "127.0.0.1", server_port=settings.port, share=False,
        allowed_paths=[str(settings.output_dir.resolve()), str(ROOT / "examples"), str(ROOT / "test1.png")],
        blocked_paths=[str(ROOT / ".env"), str(ROOT / ".venv"), str(ROOT / "models")],
        inbrowser=True, max_file_size="30mb", show_error=False,
    )


if __name__ == "__main__":
    main()
