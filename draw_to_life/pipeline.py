"""Orquestación y artefactos de cada ejecución; independiente de Gradio."""

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import secrets
import shutil
import time
from typing import Callable

from PIL import Image

from .config import Settings, STYLES, valid_hex
from .characters import CharacterFactory
from .description import describe
from .demo_character import DemoMatch, recognize_demo, personalize_demo
from .generation import INTERNAL_INSTRUCTION, LocalGenerator
from .models import local_models
from .processing import Drawing, load_image, make_references, preprocess
from .rig import (Puppet, RigError, SPECIES, composite, export_package, free_guide, load_puppet, make_guide)

LOGGER = logging.getLogger(__name__)


def write_metadata(directory: Path, metadata: dict) -> None:
    temporary = directory / "metadata.tmp"
    temporary.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(directory / "metadata.json")


@dataclass
class Run:
    directory: Path
    drawing: Drawing
    reference: Image.Image
    control: Image.Image
    palette: list[str]
    preserve_colors: bool
    metadata: dict
    started: float
    mode: str = "legacy"
    animal_override: str | None = None
    puppet: Puppet | None = None
    demo_match: DemoMatch | None = None


class Pipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.generator = LocalGenerator(settings)
        self.characters = CharacterFactory(settings)

    def prepare(self, source: str | Path, style: str, color_mode: str,
                palette: list[str], seed: int | None = None, *, mode: str = "legacy",
                animal: str | None = None) -> Run:
        if style not in STYLES:
            raise ValueError("Elegí un estilo válido.")
        if color_mode not in {"Colores del dibujo", "Paleta por defecto"}:
            raise ValueError("Elegí una opción de color válida.")
        if len(palette) != 3:
            raise ValueError("La paleta debe tener tres colores.")
        palette = [valid_hex(color) for color in palette]
        if mode not in {"auto", "template", "free", "legacy"}:
            raise ValueError("El modo debe ser auto, template, free o legacy.")
        if animal not in {None, "auto", *SPECIES}:
            raise ValueError("Elegí un animal válido del catálogo.")
        if mode != "legacy" and style != "Cartoon infantil":
            raise ValueError("Las bases animadas usan el estilo Cartoon infantil. Los estilos v1 usan mode=legacy.")
        source = Path(source)
        if not source.is_file():
            raise ValueError("Primero cargá una foto del dibujo.")
        started = time.perf_counter()
        image = load_image(source)
        timestamp = datetime.now(timezone.utc)
        directory = self.settings.output_dir / f"{timestamp:%Y%m%d_%H%M%S}_{secrets.token_hex(3)}"
        directory.mkdir(parents=True, exist_ok=False)
        shutil.copyfile(source, directory / f"original{source.suffix.lower()}")
        metadata = {
            "original_filename": source.name, "timestamp": timestamp.isoformat(),
            "status": "processing", "style": style, "color_mode": color_mode,
            "seed": seed if seed is not None else secrets.randbelow(2**31),
            "detected_colors": [], "applied_palette": [], "description": None,
            "models": {"vision": self.settings.vision_model, "image": self.settings.image_model,
                       "control": self.settings.control_model},
            "parameters": {key: value for key, value in asdict(self.settings).items()
                           if key in {"image_size", "steps", "strength", "control_scale", "guidance"}},
            "vision_image_size": 768,
            "internal_instruction": INTERNAL_INSTRUCTION if mode == "legacy" else (
                "Create a friendly animated 2D children's mascot. Use the prepared puppet geometry "
                "when available; otherwise build a new puppet from the drawing silhouette. "
                "Preserve species and palette, make small masked texture corrections, and keep "
                "facial layers, pivots, hidden attachments and animation structure intact."
            ), "warnings": [],
            "requested_mode": mode, "animal_override": animal if animal != "auto" else None,
        }
        write_metadata(directory, metadata)
        try:
            drawing = preprocess(image)
            demo_match = recognize_demo(image, drawing=drawing) if mode == "auto" and animal in {None, "auto"} else None
            if demo_match and demo_match.evidence["method"] == "sift_outline_homography":
                drawing = preprocess(demo_match.aligned)
            if demo_match:
                drawing.colors = [{"hex": value, "role": role} for role, value in demo_match.colors.items()]
                drawing.has_color = bool(demo_match.colors)
            drawing.cropped.save(directory / "cropped.png")
            drawing.isolated.save(directory / "isolated.png")
            preserve = color_mode == "Colores del dibujo" and drawing.has_color
            applied = [color["hex"] for color in drawing.colors] if preserve else palette
            if mode != "legacy":
                applied = applied[:3] + palette[len(applied[:3]):]
            if demo_match and color_mode == "Colores del dibujo":
                applied = [demo_match.colors.get(role, "#F5F3F0") for role in ("primary", "secondary", "accent")]
            reference, control = make_references(drawing, self.settings.image_size, applied, preserve)
            reference.save(directory / "generation_reference.png")
            control.save(directory / "control_scribble.png")
            warnings = list(drawing.warnings)
            if color_mode == "Colores del dibujo" and not drawing.has_color:
                warnings.append("No se detectaron colores claros; se aplicó la paleta por defecto.")
            metadata.update({"detected_colors": drawing.colors, "applied_palette": applied,
                             "preserve_drawing_colors": preserve, "bounding_box": list(drawing.bbox),
                             "bounding_box_coordinates": "original image pixels: left, top, right, bottom",
                             "original_size": list(image.size), "warnings": warnings})
            if demo_match:
                metadata["demo_recognition"] = demo_match.evidence
                if demo_match.evidence["method"] == "sift_outline_homography":
                    metadata["bounding_box_coordinates"] = "registered demo reference pixels: left, top, right, bottom"
                if color_mode == "Colores del dibujo" and not drawing.has_color:
                    metadata["warnings"] = [w for w in warnings if "paleta por defecto" not in w]
                    metadata["warnings"].append("El personaje no tiene color detectable; se conservan las zonas sin pintar claras.")
            write_metadata(directory, metadata)
            return Run(directory, drawing, reference, control, applied, preserve, metadata, started,
                       mode=mode, animal_override=animal if animal != "auto" else None, demo_match=demo_match)
        except Exception as exc:
            metadata.update({"status": "failed", "error": str(exc), "duration_seconds": round(time.perf_counter() - started, 2)})
            write_metadata(directory, metadata)
            raise

    def finish(self, run: Run, progress: Callable[[float, str], None] = lambda _fraction, _message: None) -> Path:
        try:
            if run.demo_match is not None:
                return self._finish_demo(run, progress)
            animated = run.mode != "legacy"
            effective_settings = replace(self.settings, image_model=self.settings.character_model) if animated else self.settings
            run.metadata["models"]["image"] = effective_settings.image_model
            write_metadata(run.directory, run.metadata)
            paths = local_models(effective_settings)
            run.metadata["model_revisions"] = {key: path.name for key, path in paths.items()}
            # El VLM y el generador no compiten por RAM en la misma etapa.
            self.generator.unload()
            self.characters.unload()
            progress(0.22, "Entendiendo el dibujo con visión local en CPU…")
            description, warnings = describe(run.drawing.isolated.convert("RGB"), paths["vision"], self.settings)
            run.metadata.update({"description": description.to_dict(), "status": "generating"})
            run.metadata["warnings"].extend(warnings)
            write_metadata(run.directory, run.metadata)
            if animated:
                return self._finish_character(run, paths, description, progress)
            result = self.generator.generate(
                paths, run.reference, run.control, description, run.palette,
                run.metadata["style"], run.preserve_colors, run.metadata["seed"], progress,
            )
            progress(0.97, "Guardando tu personaje…")
            final = run.directory / "final_character.png"
            result.image.save(final)
            run.metadata.update({"status": "completed", "device": result.device,
                                 "effective_prompt": result.prompt, "negative_prompt": result.negative_prompt,
                                 "duration_seconds": round(time.perf_counter() - run.started, 2)})
            run.metadata["warnings"].extend(result.warnings)
            write_metadata(run.directory, run.metadata)
            progress(1.0, "Tu dibujo ya tiene vida.")
            return final
        except Exception as exc:
            self.generator.unload()
            self.characters.unload()
            run.metadata.update({"status": "failed", "error": str(exc),
                                 "duration_seconds": round(time.perf_counter() - run.started, 2)})
            write_metadata(run.directory, run.metadata)
            LOGGER.exception("Falló la ejecución %s", run.directory.name)
            raise

    def _finish_demo(self, run, progress) -> Path:
        progress(.35, "Aplicando los colores a tu personaje…")
        puppet = personalize_demo(run.demo_match, run.palette,
                                  run.metadata["color_mode"] == "Colores del dibujo")
        run.puppet = puppet
        run.demo_match.aligned.save(run.directory / "registered_photo.png")
        final = run.directory / "final_character.png"
        composite(puppet, background="white").convert("RGB").save(final)
        package = export_package(puppet, run.directory / "character")
        run.metadata.update({"status": "completed", "generation_mode": "prepared_demo",
                             "selected_species": "stitch", "base_id": "stitch-demo",
                             "description": {"creature": puppet.manifest["creature"], "species": "stitch"},
                             "character_package": package.name, "rig_schema_version": 1,
                             "applied_palette": puppet.manifest["palette"],
                             "models": {}, "model_revisions": {}, "device": "cpu",
                             "live_model_inference": False, "generation_seconds": 0,
                             "effective_parameters": {"method": "registered_photo_region_colors"},
                             "duration_seconds": round(time.perf_counter() - run.started, 2)})
        write_metadata(run.directory, run.metadata)
        progress(1, "Tu mascota ya tiene vida.")
        return final

    def _finish_character(self, run, paths, description, progress) -> Path:
        if run.animal_override:
            description = replace(description, species=run.animal_override, species_uncertain=False)
        species = description.species
        has_species = species in SPECIES and not description.species_uncertain
        base = self.settings.catalog_dir / species
        use_template = run.mode != "free" and has_species and base.is_dir()
        if run.mode == "template" and not use_template:
            raise RigError("No hay una base preparada para ese dibujo. Elegí un animal con base disponible o usá el modo automático.")
        if use_template:
            puppet = load_puppet(base)
            progress(.35, f"Adaptando la base de {SPECIES[species]}…")
            puppet = self.characters.adapt(puppet, run.palette, paths, description, run.metadata["seed"],
                lambda fraction, message: progress(.35 + .60 * fraction, message))
            mode = "template"
        else:
            if run.mode == "auto":
                reason = "La especie no se reconoció con claridad o está fuera del catálogo." if not has_species else "La base de ese animal todavía no está preparada."
                run.metadata["warnings"].append(reason + " Se creará un personaje nuevo con IA local.")
            progress(.35, "Creando un personaje nuevo y sus piezas animables…")
            try:
                guide = free_guide(run.drawing.silhouette, self.settings.image_size, run.palette, description.creature)
            except RigError:
                # Un contorno irregular puede impedir separar una cara. Se crea
                # una estructura nueva simple y aun así se genera su arte con IA.
                guide = make_guide("unknown", self.settings.image_size, run.palette, description.creature)
                guide.manifest["id"] = "custom"
                run.metadata["warnings"].append(
                    "La silueta no permitió separar las piezas; se generó una estructura redondeada nueva.")
            puppet = self.characters.generate_parts(guide, paths, description, run.metadata["seed"],
                lambda fraction, message: progress(.35 + .60 * fraction, message), creating=True,
                checkpoint_dir=run.directory / "checkpoints")
            mode = "free"
        run.puppet = puppet
        progress(.97, "Guardando el personaje y sus animaciones…")
        final = run.directory / "final_character.png"
        composite(puppet, background="white").convert("RGB").save(final)
        package = export_package(puppet, run.directory / "character")
        provenance = puppet.manifest["provenance"]
        run.metadata["parameters"].update(provenance["parameters"])
        run.metadata.update({"status": "completed", "description": description.to_dict(),
                             "generation_mode": mode, "selected_species": species,
                             "base_id": puppet.manifest.get("base_id"),
                             "character_package": package.name, "rig_schema_version": 1,
                             "models": {"vision": self.settings.vision_model,
                                        "image": self.settings.character_model, "control": self.settings.control_model},
                             "device": provenance["device"], "corrections": provenance["parts"],
                             "effective_parameters": provenance["parameters"],
                             "generation_seconds": provenance["duration_seconds"],
                             "duration_seconds": round(time.perf_counter() - run.started, 2)})
        run.metadata["warnings"].extend(provenance["warnings"])
        run.metadata["warnings"] = list(dict.fromkeys(run.metadata["warnings"]))
        write_metadata(run.directory, run.metadata)
        progress(1, "Tu mascota ya tiene vida.")
        return final
