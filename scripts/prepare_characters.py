"""Generar las seis bases con IA local; reanudar piezas completadas al repetir."""

import argparse
from dataclasses import replace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from draw_to_life.characters import CharacterFactory  # noqa: E402
from draw_to_life.config import Settings  # noqa: E402
from draw_to_life.models import local_models  # noqa: E402
from draw_to_life.rig import SPECIES, catalog_status, export_package  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Preparar mascotas animables con IA local")
    parser.add_argument("--animal", choices=["all", *SPECIES], default="all")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--force", action="store_true", help="Regenerar conservando un backup de la base anterior")
    parser.add_argument("--status", action="store_true", help="Verificar el catálogo sin cargar modelos")
    args = parser.parse_args()
    settings = Settings.from_env()
    if args.status:
        report = catalog_status(settings.catalog_dir)
        print(report)
        return 0 if report["complete"] else 1
    factory = CharacterFactory(settings)
    try:
        paths = local_models(replace(settings, image_model=settings.character_model))
        animals = list(SPECIES) if args.animal == "all" else [args.animal]
        for species in animals:
            print(f"\nPreparando {SPECIES[species]}…", flush=True)
            puppet = factory.prepare_base(species, paths, args.seed,
                lambda fraction, message: print(f"{fraction:.0%} · {message}", flush=True), force=args.force)
            # Preview independiente + bundle del catálogo, separado de outputs de usuarios.
            export_package(puppet, settings.catalog_dir / species)
            archive = settings.catalog_dir / "character.zip"
            archive.replace(settings.catalog_dir / f"{species}.zip")
            print(f"Listo: {settings.catalog_dir / species}", flush=True)
        return 0
    except Exception as exc:
        print(f"No se pudo preparar el catálogo: {exc}", file=sys.stderr)
        return 1
    finally:
        factory.unload()


if __name__ == "__main__":
    raise SystemExit(main())
