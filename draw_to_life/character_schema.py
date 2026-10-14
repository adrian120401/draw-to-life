"""Contrato del personaje, independiente de los modelos y del renderer."""

import math
from pathlib import Path, PureWindowsPath


class RigError(ValueError):
    pass


def validate_manifest(data: dict, directory: Path | None = None) -> None:
    if not isinstance(data, dict) or type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        raise RigError("Versión de personaje incompatible.")
    canvas = data.get("canvas")
    if not isinstance(canvas, list) or len(canvas) != 2 or any(
            type(v) is not int or not 128 <= v <= 2048 for v in canvas):
        raise RigError("Lienzo inválido.")
    layers = data.get("layers", [])
    if not isinstance(layers, list) or not all(isinstance(layer, dict) for layer in layers):
        raise RigError("Las piezas deben ser una lista de objetos.")
    ids = [layer.get("id") for layer in layers]
    if not layers or any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
        raise RigError("Las piezas deben tener identificadores únicos.")
    parents = {layer["id"]: layer.get("parent") for layer in layers}
    # Validar todas las referencias antes de recorrer cadenas: un hijo puede
    # aparecer antes del padre que contiene la referencia inválida.
    if any(parent is not None and (not isinstance(parent, str) or parent not in parents)
           for parent in parents.values()):
        raise RigError("La unión apunta a una pieza inexistente.")
    for layer in layers:
        seen, current = set(), layer["id"]
        while current is not None:
            if current in seen:
                raise RigError("Las uniones forman un ciclo.")
            seen.add(current)
            current = parents[current]
        pivot = layer.get("pivot")
        if not isinstance(pivot, list) or len(pivot) != 2 or any(
                type(v) not in (int, float) or not math.isfinite(v) for v in pivot):
            raise RigError("Pivote inválido.")
        if not isinstance(layer.get("texture"), str):
            raise RigError("Ruta de textura inválida.")
        path = Path(layer["texture"])
        windows_path = PureWindowsPath(layer["texture"])
        if (path.anchor or windows_path.anchor or ".." in path.parts
                or ".." in windows_path.parts or path.suffix.lower() != ".png"):
            raise RigError("Ruta de textura inválida.")
        if directory is not None:
            from PIL import Image
            resolved = (directory / path).resolve()
            if not resolved.is_relative_to(directory.resolve()):
                raise RigError("La textura sale del paquete.")
            with Image.open(resolved) as texture:
                if texture.mode != "RGBA" or list(texture.size) != canvas:
                    raise RigError("Cada textura debe ser RGBA y compartir el lienzo.")
                if texture.getchannel("A").getbbox() is None:
                    raise RigError("Una pieza está vacía.")
    animations = data.get("animations", {})
    if not isinstance(animations, dict) or not {"idle", "blink", "react"} <= animations.keys():
        raise RigError("Faltan animaciones básicas.")
    for animation in animations.values():
        if not isinstance(animation, dict) or not isinstance(animation.get("duration"), (int, float)) or not 0 < animation["duration"] < 60:
            raise RigError("Duración de animación inválida.")
    required_numbers = {"idle": ("breath_scale", "head_degrees"),
                        "blink": ("interval",), "react": ("jump", "tilt_degrees")}
    for name, fields in required_numbers.items():
        for field in fields:
            value = animations[name].get(field)
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                raise RigError("Parámetro de animación inválido.")
    if animations["blink"]["interval"] <= animations["blink"]["duration"]:
        raise RigError("El intervalo de parpadeo debe superar su duración.")

