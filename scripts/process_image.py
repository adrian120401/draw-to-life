"""Ejecutar el mismo pipeline sin interfaz, útil para validar la instalación."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from draw_to_life.config import Settings, STYLES  # noqa: E402
from draw_to_life.pipeline import Pipeline  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Convertir un dibujo en un personaje 2D local")
    parser.add_argument("image", type=Path)
    parser.add_argument("--style", choices=list(STYLES), default="Cartoon infantil")
    parser.add_argument("--mode", choices=["auto", "template", "free", "legacy"], default=None,
                        help="Por defecto: auto para Cartoon infantil, legacy para los estilos v1")
    parser.add_argument("--animal", choices=["auto", "dog", "cat", "duck", "pig", "rabbit", "bear"], default="auto")
    parser.add_argument("--default-palette", action="store_true")
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    settings = Settings.from_env()
    pipeline = Pipeline(settings)
    mode = args.mode or ("auto" if args.style == "Cartoon infantil" else "legacy")
    try:
        run = pipeline.prepare(args.image, args.style,
                               "Paleta por defecto" if args.default_palette else "Colores del dibujo",
                               list(settings.palette), seed=args.seed, mode=mode, animal=args.animal)
        result = pipeline.finish(run, lambda fraction, message: print(f"{fraction:.0%} · {message}", flush=True))
        print(f"Resultado: {result}")
        return 0
    except Exception as exc:
        print(f"No se pudo generar el personaje: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
