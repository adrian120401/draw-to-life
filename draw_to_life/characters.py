"""Creación previa y personalización por piezas, exclusivamente con IA local."""

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image, ImageOps

from .config import Settings
from .description import CharacterDescription
from .generation import LocalGenerator
from .expressions import with_expressions
from .rig import (Puppet, RigError, SPECIES, apply_palette, layer_reference, load_puppet,
                  make_guide, project_texture, recolor, save_puppet)

PART_NEGATIVE = (
    "photo, realistic, 3d render, scary, human, eyes, mouth, face, text, watermark, "
    "extra objects, paper texture, messy sketch, patterned surface"
)


def texture_input(texture: Image.Image, size: int) -> tuple[Image.Image, Image.Image, tuple, tuple]:
    bbox = texture.getchannel("A").getbbox()
    if bbox is None:
        raise RigError("La pieza está vacía.")
    cropped = texture.crop(bbox)
    contained = ImageOps.contain(cropped, (round(size * .82),) * 2, Image.Resampling.LANCZOS)
    offset = ((size - contained.width) // 2, (size - contained.height) // 2)
    input_texture = Image.new("RGBA", (size, size))
    input_texture.paste(contained, offset)
    reference, control = layer_reference(input_texture)
    content_box = (offset[0], offset[1], offset[0] + contained.width, offset[1] + contained.height)
    return reference, control, bbox, content_box


def place_texture(image: Image.Image, original: Image.Image, bbox: tuple, content_box: tuple,
                  *, face_bounds=None) -> Image.Image:
    width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
    patch = image.crop(content_box).resize((width, height), Image.Resampling.LANCZOS)
    projected = Image.new("RGB", original.size, "white")
    projected.paste(patch, bbox[:2])
    return project_texture(projected, original, blank_face=face_bounds is not None, face_bounds=face_bounds)


def transfer_appendages(puppet: Puppet) -> None:
    for layer in puppet.manifest["layers"]:
        source = layer.get("texture_source")
        if not source:
            continue
        texture = puppet.textures[source]
        target = puppet.textures[layer["id"]]
        source_bbox = texture.getchannel("A").getbbox()
        target_bbox = target.getchannel("A").getbbox()
        source_rgba = np.array(texture.crop(source_bbox))
        active = source_rgba[:, :, 3] > 128
        source_rgb = source_rgba[:, :, :3].copy()
        source_rgb[~active] = np.median(source_rgb[active], axis=0).astype(np.uint8)
        patch = ImageOps.fit(Image.fromarray(source_rgb),
                             (target_bbox[2] - target_bbox[0], target_bbox[3] - target_bbox[1]))
        canvas = Image.new("RGB", target.size)
        canvas.paste(patch, target_bbox[:2])
        # Preserve the appendage's contour and the completed hidden attachment.
        puppet.textures[layer["id"]] = project_texture(canvas, target)


class CharacterFactory:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.generator = LocalGenerator(replace(settings, image_model=settings.character_model,
                                                image_size=settings.part_image_size,
                                                strength=settings.adaptation_strength))

    def unload(self):
        self.generator.unload()

    def generate_parts(self, puppet: Puppet, paths: dict, description: CharacterDescription,
                       seed: int, progress=lambda _fraction, _message: None, *,
                       creating: bool = False, checkpoint_dir: Path | None = None) -> Puppet:
        result = Puppet(deepcopy(puppet.manifest), {key: value.copy() for key, value in puppet.textures.items()})
        settings = replace(self.generator.settings,
                           strength=self.settings.catalog_strength if creating else self.settings.adaptation_strength,
                           steps=self.settings.catalog_steps if creating else self.settings.steps)
        self.generator.settings = settings
        parts = [layer for layer in result.manifest["layers"] if layer.get("generated")]
        if not parts:
            raise RigError("El personaje no tiene piezas para generar con IA.")
        records, warnings, devices = [], [], []
        start = time.perf_counter()
        for index, layer in enumerate(parts):
            name = layer["id"]
            reference, control, bbox, content_box = texture_input(result.textures[name], settings.image_size)
            # Featureless skin is deliberate: eyes and mouth are separate assets.
            # Accessory details go on the torso, never across a moving joint.
            features = description.accessories if name == "body" else ""
            prompt = (
                "one rounded cartoon shape, smooth blank surface, vibrant color, "
                "soft cel shading, children's game mascot texture, clean outline, white background"
            )
            if creating and result.manifest["species"] == "unknown":
                prompt += ", " + description.creature[:70] + ", " + description.shape[:60]
            if features:
                prompt += ", " + features[:70]
            # Paths contain the pinned local revisions used in this run.
            fingerprint = hashlib.sha256(json.dumps({
                "prompt": prompt, "seed": seed + index, "settings": {
                    "strength": settings.strength, "steps": settings.steps,
                    "size": settings.image_size, "control_scale": settings.control_scale,
                    "guidance": settings.guidance},
                "model": {key: str(value) for key, value in paths.items()},
                "reference": hashlib.sha256(reference.tobytes()).hexdigest(),
            }, sort_keys=True).encode()).hexdigest()
            cached = checkpoint_dir / (fingerprint + ".png") if checkpoint_dir else None
            info = cached.with_suffix(".json") if cached else None
            generated_image, record = None, None
            if cached and cached.is_file() and info.is_file():
                try:
                    with Image.open(cached) as image:
                        restored = image.copy()
                    restored_record = json.loads(info.read_text(encoding="utf-8"))
                    if (restored.size == reference.size and np.array(restored).std() >= .5 and
                            isinstance(restored_record, dict) and
                            {"layer", "seed", "prompt", "negative_prompt", "device", "warnings"} <= restored_record.keys()):
                        generated_image, record = restored, restored_record
                        record["reused_checkpoint"] = True
                        progress(index / len(parts), f"Reutilizando la pieza {name}…")
                except (OSError, ValueError):
                    # Una interrupción puede dejar un checkpoint parcial. Es
                    # trabajo temporal: rehacer solo esa pieza, no toda la base.
                    pass
            if generated_image is None:
                generated = self.generator.generate(
                    paths, reference, control, description, result.manifest["palette"],
                    "Cartoon infantil", True, seed + index,
                    lambda fraction, message: progress((index + fraction) / len(parts), f"{name} · {message}"),
                    prompt_override=prompt, negative_override=PART_NEGATIVE,
                )
                generated_image = generated.image
                record = {"layer": name, "seed": seed + index, "prompt": generated.prompt,
                          "negative_prompt": generated.negative_prompt, "device": generated.device,
                          "warnings": generated.warnings, "reused_checkpoint": False}
                if cached:
                    checkpoint_dir.mkdir(parents=True, exist_ok=True)
                    generated_image.save(cached)
                    temporary = info.with_suffix(".tmp")
                    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
                    temporary.replace(info)
            if generated_image.size != reference.size or np.array(generated_image).std() < .5:
                raise RigError(f"El modelo produjo una textura inválida para {name}.")
            result.textures[name] = place_texture(
                generated_image, result.textures[name], bbox, content_box,
                face_bounds=result.manifest.get("face_bounds") if name == "head" else None,
            )
            role = layer.get("color_role")
            if role:
                color = result.manifest["palette"][{"primary": 0, "secondary": 1, "accent": 2}[role]]
                result.textures[name] = recolor(result.textures[name], color)
            records.append(record)
            warnings.extend(record.get("warnings", []))
            devices.append(record["device"])
        transfer_appendages(result)
        result.manifest["provenance"] = {
            "status": "generated", "operation": "create" if creating else "adapt",
            "model": self.settings.character_model, "model_revision": paths["image"].name,
            "control_revision": paths["control"].name, "parts": records,
            "parameters": {"strength": settings.strength, "steps": settings.steps,
                           "part_image_size": settings.image_size, "control_scale": settings.control_scale,
                           "guidance": settings.guidance},
            "duration_seconds": round(time.perf_counter() - start, 2),
            "device": ",".join(dict.fromkeys(devices)), "warnings": list(dict.fromkeys(warnings)),
            "face": "separate procedural eye and mouth textures",
        }
        result.manifest["description"] = description.to_dict()
        progress(1, "Piezas listas para animar.")
        return result

    def prepare_base(self, species: str, paths: dict, seed: int = 42,
                     progress=lambda _fraction, _message: None, *, force: bool = False) -> Puppet:
        if species not in SPECIES:
            raise RigError("El animal no pertenece al catálogo.")
        destination = self.settings.catalog_dir / species
        if destination.exists() and not force:
            # A corrupt existing base is an error, never overwritten implicitly.
            return load_puppet(destination)
        guide = make_guide(species, self.settings.image_size)
        description = CharacterDescription(creature=species, species=species, species_uncertain=False)
        work = self.settings.catalog_dir / ".work" / species
        puppet = self.generate_parts(guide, paths, description, seed, progress,
                                     creating=True, checkpoint_dir=work / "checkpoints")
        puppet.manifest["provenance"]["seed"] = seed
        save_puppet(puppet, work / "candidate")
        # Publish only a fully validated character. Keep replaced bases for recovery.
        load_puppet(work / "candidate")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            backup = destination.with_name(species + f".backup-{time.time_ns()}")
            destination.rename(backup)
        (work / "candidate").rename(destination)
        return puppet

    def adapt(self, puppet: Puppet, palette: list[str], paths: dict,
              description: CharacterDescription, seed: int, progress) -> Puppet:
        adapted = self.generate_parts(apply_palette(with_expressions(puppet), palette), paths, description, seed, progress)
        adapted.manifest["base_id"] = puppet.manifest["id"]
        adapted.manifest["base_provenance"] = puppet.manifest["provenance"]
        return adapted
