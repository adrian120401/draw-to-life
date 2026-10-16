"""Expresiones locales alineadas a la cara del rig, sin regenerar su arte."""

from copy import deepcopy


def with_expressions(puppet):
    """Enriquecer también bases v1 anteriores sin modificar el catálogo."""
    from PIL import Image, ImageDraw

    result = type(puppet)(deepcopy(puppet.manifest), dict(puppet.textures))
    eyes = [layer for layer in result.manifest["layers"] if layer.get("motion") == "blink"]
    eye_widths = []
    for layer in eyes:
        texture = result.textures[layer["id"]]
        bounds = texture.getchannel("A").getbbox()
        if bounds is None:
            continue
        left, top, right, bottom = bounds
        eye_widths.append(right - left)
        for name in ("happy", "closed"):
            face = Image.new("RGBA", texture.size)
            draw = ImageDraw.Draw(face)
            height = bottom - top
            cy = (top + bottom) / 2
            box = (left, cy - height * .18, right - 1, cy + height * .22)
            draw.arc(box, 185 if name == "happy" else 0,
                     355 if name == "happy" else 180, fill="#302D45",
                     width=max(2, round((right - left) * .13)))
            key = f"{layer['id']}__{name}"
            result.textures[key] = face
            layer.setdefault("expressions", {})[name] = f"textures/{key}.png"

    scale = sum(eye_widths) / len(eye_widths) / 41 if eye_widths else result.manifest["canvas"][0] / 512
    for layer in result.manifest["layers"]:
        if layer.get("motion") != "smile":
            continue
        original = result.textures[layer["id"]]
        x, y = layer["pivot"]
        species = result.manifest.get("species")
        # La textura antigua también contiene nariz/narinas. Conservarlas
        # y reemplazar únicamente la zona de la boca en cada variante.
        if species == "pig":
            y += 9 * scale
        cut = round(y if species != "duck" else y - 18 * scale)
        for name in ("happy", "open", "chew"):
            face = original.copy()
            face.paste((0, 0, 0, 0), (0, max(0, cut), face.width, face.height))
            draw = ImageDraw.Draw(face)
            width = max(2, round(3 * scale))
            if name == "happy":
                box = (x - 21 * scale, y - 7 * scale, x + 21 * scale, y + 22 * scale)
                draw.chord(box, 0, 180, fill="#443348")
                draw.ellipse((x - 10 * scale, y + 11 * scale, x + 10 * scale, y + 19 * scale), fill="#EF91AB")
            elif name == "open":
                draw.ellipse((x - 14 * scale, y, x + 14 * scale, y + 27 * scale), fill="#443348")
                draw.ellipse((x - 8 * scale, y + 17 * scale, x + 9 * scale, y + 24 * scale), fill="#EF91AB")
            else:
                draw.arc((x - 16 * scale, y - 4 * scale, x + 16 * scale, y + 13 * scale),
                         0, 180, fill="#443348", width=width)
            key = f"{layer['id']}__{name}"
            result.textures[key] = face
            layer.setdefault("expressions", {})[name] = f"textures/{key}.png"
        layer["mouth_anchor"] = [x, y + 9 * scale]
    result.manifest["expression_provenance"] = {
        "method": "procedural", "version": 1,
        "source": "Existing facial textures, alpha bounds and pivots; no model inference.",
    }
    return result


def texture_entries(manifest):
    """Identificador y ruta de las texturas de reposo y sus variantes."""
    for layer in manifest["layers"]:
        yield layer["id"], layer.get("texture")
        for name, path in layer.get("expressions", {}).items():
            yield f"{layer['id']}__{name}", path
