"""Rig 2D portable. Las texturas comparten un lienzo y pivotes en píxeles.

Las guías son insumos estructurales para el modelo, nunca una mascota de
reemplazo cuando falla la IA. La cara se mantiene separada y controlable.
"""

from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
import shutil
import zipfile

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from PIL.PngImagePlugin import PngInfo

from .config import ROOT, valid_hex
from .character_schema import RigError, validate_manifest
from .expressions import texture_entries, with_expressions

SPECIES = {"dog": "Perro", "cat": "Gato", "duck": "Pato", "pig": "Cerdo",
           "rabbit": "Conejo", "bear": "Oso"}
DEFAULT_PALETTES = {
    "dog": ["#F2AD63", "#FFE9C6", "#ED8096"],
    "cat": ["#AF9CEA", "#F7EDD7", "#F28DB1"],
    "duck": ["#F8D75A", "#FFAA42", "#F08B86"],
    "pig": ["#F8A4B6", "#FFD9DF", "#DE658E"],
    "rabbit": ["#80C9E7", "#E5F5FC", "#F69BB9"],
    "bear": ["#C18B65", "#FFE4BA", "#F6A179"],
    "unknown": ["#91CDB5", "#FFE2A8", "#F39AA8"],
}
RUNTIME = ROOT / "draw_to_life" / "web" / "character-player.js"


@dataclass
class Puppet:
    manifest: dict
    textures: dict[str, Image.Image]


def _shaded(mask: Image.Image, color: str, outline: bool = True) -> Image.Image:
    """Guía con volumen suave y máscara exacta, independiente del modelo."""
    size = mask.width
    yy, xx = np.mgrid[:size, :size] / size
    rgb = np.array([int(color[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)
    light = np.exp(-(((xx - .36) / .43) ** 2 + ((yy - .30) / .5) ** 2))
    shade = np.clip(.72 + .29 * light, .72, 1.04)
    fill = rgb[None, None, :] * shade[:, :, None]
    fill += (255 - fill) * (.09 * light[:, :, None])
    alpha = np.array(mask)
    if outline:
        inner = cv2.erode(alpha, np.ones((5, 5), np.uint8))
        edge = alpha > inner
        fill[edge] = rgb * .37
    return Image.fromarray(np.dstack((np.clip(fill, 0, 255).astype(np.uint8), alpha)))


def make_guide(species: str, size: int = 512, palette: list[str] | None = None,
               creature: str = "friendly creature") -> Puppet:
    """Una estructura por especie; todas las piezas incluyen solapas ocultas."""
    default = DEFAULT_PALETTES.get(species, DEFAULT_PALETTES["unknown"])
    if palette is not None and not palette:
        raise RigError("La paleta está vacía.")
    palette = [valid_hex(c) for c in (palette if palette is not None else default)]
    palette = (palette[:3] + default[len(palette[:3]):])[:3]
    textures, layers = {}, []
    scale = size / 512

    def layer(name, parent, pivot, role, shapes, motion="", generated=True):
        mask = Image.new("L", (512, 512))
        drawing = ImageDraw.Draw(mask)
        for kind, points in shapes:
            if kind == "ellipse":
                drawing.ellipse(points, fill=255)
            elif kind == "polygon":
                drawing.polygon(points, fill=255)
            elif kind == "rounded":
                drawing.rounded_rectangle(points, radius=35, fill=255)
        if size != 512:
            mask = mask.resize((size, size), Image.Resampling.LANCZOS)
        color = palette[{"primary": 0, "secondary": 1, "accent": 2}.get(role, 0)]
        textures[name] = _shaded(mask, color)
        layers.append({"id": name, "parent": parent, "pivot": [round(v * scale, 3) for v in pivot],
                       "texture": f"textures/{name}.png", "color_role": role,
                       "motion": motion, "generated": generated})

    # Detrás del torso. La cola tiene una unión cubierta por el cuerpo.
    if species in {"dog", "cat", "pig", "bear", "rabbit"}:
        tail_shapes = [("ellipse", (330, 346, 398, 422))]
        if species == "cat":
            tail_shapes = [("rounded", (336, 285, 378, 413))]
        layer("tail", "body", (344, 390), "primary", tail_shapes, "sway")
    layer("body", None, (256, 442), "primary", [
        ("ellipse", (172, 271, 340, 446)),
        ("ellipse", (159, 388, 233, 459)), ("ellipse", (279, 388, 353, 459)),
    ], "breathe")
    layer("belly", "body", (256, 367), "secondary", [("ellipse", (203, 318, 309, 424))], generated=False)
    if species == "duck":
        layer("wing_left", "body", (177, 325), "primary", [("ellipse", (141, 318, 202, 395))], "sway")
        layer("wing_right", "body", (335, 325), "primary", [("ellipse", (310, 318, 371, 395))], "sway")
    ear_shapes = {
        "dog": [("ellipse", (83, 113, 163, 292))],
        "cat": [("polygon", [(119, 171), (115, 67), (207, 133)])],
        "rabbit": [("ellipse", (143, 32, 205, 206))],
        "pig": [("polygon", [(132, 179), (112, 85), (211, 140)])],
        "bear": [("ellipse", (107, 92, 183, 175))],
    }
    if species in ear_shapes:
        layer("ear_left", "head", (154, 164), "primary", ear_shapes[species], "sway")
        # Mirroring the guide gives exact symmetry, not another learned variant.
        mask = textures["ear_left"].getchannel("A").transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        textures["ear_right"] = _shaded(mask, palette[0])
        layers.append({**layers[-1], "id": "ear_right", "pivot": [358 * scale, 164 * scale],
                       "texture": "textures/ear_right.png"})
    layer("head", "body", (256, 298), "primary", [("ellipse", (119, 116, 393, 329))], "head")
    if species in {"dog", "bear", "cat", "rabbit"}:
        layer("muzzle", "head", (256, 275), "secondary", [("ellipse", (209, 252, 303, 310))], generated=False)
    if species == "pig":
        layer("snout", "head", (256, 278), "accent", [("ellipse", (220, 255, 292, 301))], generated=False)
    if species == "duck":
        layer("bill", "head", (256, 278), "secondary", [("ellipse", (201, 258, 311, 304))], generated=False)
    layer("blush", "head", (256, 258), "accent", [
        ("ellipse", (174, 246, 198, 264)), ("ellipse", (314, 246, 338, 264))], generated=False)
    blush_mask = textures["blush"].getchannel("A").point(lambda value: round(value * .62))
    textures["blush"] = _shaded(blush_mask, palette[2], outline=False)
    # Texturas faciales originales de cada base; no dependen de coordenadas VLM.
    for name, x in (("eye_left", 207), ("eye_right", 305)):
        image = Image.new("RGBA", (512, 512))
        draw = ImageDraw.Draw(image)
        draw.ellipse((x - 20, 198, x + 20, 247), fill="#302D45")
        draw.ellipse((x - 9, 205, x + 3, 219), fill="white")
        draw.ellipse((x + 4, 228, x + 10, 234), fill="#D5E6FF")
        textures[name] = image.resize((size, size), Image.Resampling.LANCZOS)
        layers.append({"id": name, "parent": "head", "pivot": [x * scale, 224 * scale],
                       "texture": f"textures/{name}.png", "color_role": None, "motion": "blink", "generated": False})
    face = Image.new("RGBA", (512, 512))
    drawing = ImageDraw.Draw(face)
    if species == "pig":
        for x in (243, 269):
            drawing.ellipse((x - 4, 270, x + 4, 282), fill="#A9456A")
        drawing.arc((239, 285, 274, 303), 0, 180, fill="#63394C", width=4)
    elif species == "duck":
        drawing.arc((232, 268, 280, 292), 0, 180, fill="#8A5629", width=4)
    else:
        drawing.rounded_rectangle((245, 261, 267, 274), radius=6, fill="#443348")
        drawing.line((256, 271, 256, 280), fill="#443348", width=4)
        drawing.arc((235, 271, 256, 291), 0, 150, fill="#443348", width=4)
        drawing.arc((256, 271, 277, 291), 30, 180, fill="#443348", width=4)
    textures["mouth"] = face.resize((size, size), Image.Resampling.LANCZOS)
    layers.append({"id": "mouth", "parent": "head", "pivot": [256 * scale, 280 * scale],
                   "texture": "textures/mouth.png", "color_role": None, "motion": "smile", "generated": False})
    # Apéndices usan el acabado de la cabeza/cuerpo ya generado. No volver
    # a ejecutar difusión para una oreja simétrica o una cola pequeña.
    for item in layers:
        if item["id"] in {"ear_left", "ear_right", "tail", "wing_left", "wing_right"}:
            item["generated"] = False
            item["texture_source"] = "head" if item["id"].startswith("ear") else "body"
    manifest = {"schema_version": 1, "id": species, "species": species, "creature": creature,
                "name": SPECIES.get(species, "Nueva criatura"), "canvas": [size, size],
                "palette": palette, "layers": layers, "face_bounds": [153 * scale, 162 * scale, 359 * scale, 306 * scale], "animations": {
                    "idle": {"duration": 3.2, "loop": True, "breath_scale": .018, "head_degrees": 1.5},
                    "blink": {"duration": .18, "interval": 4.3},
                    "react": {"duration": .85, "jump": .025, "tilt_degrees": 8}},
                "provenance": {"status": "guide", "note": "Structural input; not AI-generated art."}}
    return with_expressions(Puppet(manifest, textures))


def free_guide(silhouette: np.ndarray, size: int, palette: list[str], creature: str) -> Puppet:
    """Rig mínimo nuevo usando la silueta del dibujo, no una base de animal."""
    mask = Image.fromarray(silhouette).convert("L")
    bbox = mask.getbbox()
    if bbox is None:
        raise RigError("La silueta está vacía.")
    mask = ImageOps.contain(mask.crop(bbox), (round(size * .82), round(size * .82)))
    canvas = Image.new("L", (size, size))
    left, top = (size - mask.width) // 2, (size - mask.height) // 2
    canvas.paste(mask, (left, top))
    alpha = np.array(canvas)
    split = top + round(mask.height * .61)
    head, body = alpha.copy(), alpha.copy()
    head[split:, :] = 0
    body[:max(top, split - round(mask.height * .12)), :] = 0
    if np.count_nonzero(head) < 50 or np.count_nonzero(body) < 50:
        raise RigError("La silueta no permite separar cuerpo y cabeza.")
    distances = cv2.distanceTransform((head > 128).astype(np.uint8), cv2.DIST_L2, 5)
    _, radius, _, center = cv2.minMaxLoc(distances)
    if radius < size * .025:
        raise RigError("No hay una región suficiente para una cara animable.")
    cx, cy = center
    face_scale = min(radius / (size * .22), 1.0)
    standard = make_guide("unknown", size, palette, creature)
    layers, textures = [], {}
    for name, parent, pivot, piece, motion in (
        ("body", None, [cx, top + mask.height * .92], body, "breathe"),
        ("head", "body", [cx, split - mask.height * .06], head, "head"),
    ):
        textures[name] = _shaded(Image.fromarray(piece), palette[0])
        layers.append({"id": name, "parent": parent, "pivot": pivot, "texture": f"textures/{name}.png",
                       "color_role": "primary", "motion": motion, "generated": True})
    for original in standard.manifest["layers"]:
        if original["id"] not in {"eye_left", "eye_right", "mouth", "blush"}:
            continue
        item = deepcopy(original)
        ox, oy = original["pivot"]
        tx = cx + (ox - size * .5) * face_scale
        ty = cy + (oy - size * 224 / 512) * face_scale
        item["pivot"] = [tx, ty]
        inverse = (1 / face_scale, 0, size * .5 - cx / face_scale,
                   0, 1 / face_scale, size * 224 / 512 - cy / face_scale)
        textures[item["id"]] = standard.textures[item["id"]].transform(
            (size, size), Image.Transform.AFFINE, inverse, resample=Image.Resampling.BICUBIC)
        layers.append(item)
    manifest = deepcopy(standard.manifest)
    manifest.update({"id": "custom", "layers": layers,
                     "face_bounds": [cx - radius * .95, cy - radius * .7,
                                     cx + radius * .95, cy + radius * .95]})
    return with_expressions(Puppet(manifest, textures))


def recolor(texture: Image.Image, color: str) -> Image.Image:
    """Cambiar tono/saturación conservando el sombreado y los contornos."""
    valid_hex(color)
    rgba = np.array(texture.convert("RGBA"))
    hsv = cv2.cvtColor(rgba[:, :, :3], cv2.COLOR_RGB2HSV)
    target = np.array([[[int(color[i:i + 2], 16) for i in (1, 3, 5)]]], np.uint8)
    wanted = cv2.cvtColor(target, cv2.COLOR_RGB2HSV)[0, 0]
    active = rgba[:, :, 3] > 0
    # Contornos oscuros siguen oscuros; no destruir los ojos (otra capa).
    old_value = max(1, float(np.percentile(hsv[:, :, 2][active], 85)))
    hsv[:, :, 0][active] = wanted[0]
    hsv[:, :, 1][active] = wanted[1]
    hsv[:, :, 2][active] = np.clip(hsv[:, :, 2][active].astype(float) * wanted[2] / old_value, 0, 255)
    rgba[:, :, :3] = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
    return Image.fromarray(rgba)


def apply_palette(puppet: Puppet, palette: list[str]) -> Puppet:
    if not palette:
        raise RigError("La paleta está vacía.")
    colors = [valid_hex(c) for c in palette]
    defaults = puppet.manifest["palette"]
    colors = (colors[:3] + defaults[len(colors[:3]):])[:3]
    result = Puppet(deepcopy(puppet.manifest), {key: value.copy() for key, value in puppet.textures.items()})
    result.manifest["palette"] = colors
    for layer in result.manifest["layers"]:
        role = layer.get("color_role")
        if role:
            result.textures[layer["id"]] = recolor(result.textures[layer["id"]], colors[
                {"primary": 0, "secondary": 1, "accent": 2}[role]])
    return result


def composite(puppet: Puppet, *, background: str | None = None) -> Image.Image:
    image = Image.new("RGBA", tuple(puppet.manifest["canvas"]), background or (0, 0, 0, 0))
    for layer in puppet.manifest["layers"]:
        image = Image.alpha_composite(image, puppet.textures[layer["id"]])
    return image


def layer_reference(texture: Image.Image) -> tuple[Image.Image, Image.Image]:
    canvas = Image.new("RGBA", texture.size, "white")
    reference = Image.alpha_composite(canvas, texture).convert("RGB")
    edges = cv2.Canny(np.array(reference), 55, 140)
    return reference, Image.fromarray(edges).convert("RGB")


def project_texture(image: Image.Image, guide: Image.Image, *, blank_face: bool = False,
                    face_bounds: list[float] | None = None) -> Image.Image:
    """La IA modifica textura, nunca alpha/uniones. La región facial queda libre."""
    rgba = np.array(guide.convert("RGBA"))
    generated = np.array(image.convert("RGB").resize(guide.size))
    rgb = generated.astype(float)
    mask = rgba[:, :, 3]
    # Restaurar la línea del borde para que dos piezas sigan encajando.
    inner = cv2.erode(mask, np.ones((7, 7), np.uint8))
    edge = mask > inner
    rgb[edge] = rgba[:, :, :3][edge]
    # El generador podría introducir ojos en una superficie de cabeza. Reservar
    # toda la zona de cara, suavizando la unión, elimina caras duplicadas.
    if blank_face:
        face = Image.new("L", guide.size)
        drawing = ImageDraw.Draw(face)
        s = guide.width / 512
        bounds = face_bounds or [v * s for v in (153, 162, 359, 306)]
        drawing.ellipse(tuple(round(v) for v in bounds), fill=255)
        blend = np.array(face.filter(ImageFilter.GaussianBlur(9 * s)))[:, :, None] / 255
        rgb = rgb * (1 - blend) + rgba[:, :, :3] * blend
    rgb[mask == 0] = 0
    return Image.fromarray(np.dstack((np.clip(rgb, 0, 255).astype(np.uint8), mask)))


def load_puppet(directory: Path, *, require_generated: bool = True) -> Puppet:
    try:
        data = json.loads((directory / "character.json").read_text(encoding="utf-8"))
        validate_manifest(data, directory)
        provenance = data.get("provenance")
        if require_generated and (not isinstance(provenance, dict) or provenance.get("status") != "generated"):
            raise RigError("La base todavía no fue generada con IA local.")
        textures = {}
        for key, path in texture_entries(data):
            with Image.open(directory / path) as image:
                textures[key] = image.copy()
        return Puppet(data, textures)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RigError(f"Base inválida en {directory.name}: {exc}") from exc


def catalog_status(directory: Path) -> dict:
    ready, errors = [], {}
    for species in SPECIES:
        try:
            load_puppet(directory / species)
            ready.append(species)
        except RigError as exc:
            errors[species] = str(exc)
    return {"ready": ready, "errors": errors, "complete": len(ready) == len(SPECIES)}


def save_puppet(puppet: Puppet, directory: Path) -> Path:
    validate_manifest(puppet.manifest)
    directory.mkdir(parents=True, exist_ok=True)
    for key, relative in texture_entries(puppet.manifest):
        path = directory / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        info = None
        if "__" in key:
            info = PngInfo()
            info.add_text("Description", "Procedural facial expression derived from the character's existing face textures and pivots.")
            info.add_text("Software", "Draw to Life")
        puppet.textures[key].save(path, pnginfo=info)
    for layer in puppet.manifest["layers"]:
        mask_path = directory / "masks" / (layer["id"] + ".png")
        mask_path.parent.mkdir(parents=True, exist_ok=True)
        puppet.textures[layer["id"]].getchannel("A").save(mask_path)
        if layer.get("generated"):
            reference, control = layer_reference(puppet.textures[layer["id"]])
            guides = directory / "guides"
            guides.mkdir(exist_ok=True)
            reference.save(guides / (layer["id"] + "_reference.png"))
            control.save(guides / (layer["id"] + "_control.png"))
    manifest = directory / "character.json"
    temporary = directory / "character.tmp"
    temporary.write_text(json.dumps(puppet.manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(manifest)
    composite(puppet).save(directory / "preview.png")
    validate_manifest(puppet.manifest, directory)
    return manifest


def export_package(puppet: Puppet, directory: Path) -> Path:
    save_puppet(puppet, directory)
    shutil.copyfile(RUNTIME, directory / "character-player.js")
    from .preview import preview_document
    preview = preview_document(puppet)
    (directory / "index.html").write_text(preview, encoding="utf-8")
    archive = directory.parent / "character.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                bundle.write(path, path.relative_to(directory).as_posix())
    return archive
