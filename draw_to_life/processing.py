"""Aislamiento pragmático para un dibujo principal sobre papel claro.

Se separan los trazos (para ControlNet) de la silueta rellena (para preservar
el interior del personaje). No se usa un segmentador entrenado con fotos.
"""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError
from pillow_heif import register_heif_opener

register_heif_opener(thumbnails=False)

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif")


class DrawingError(ValueError):
    """Entrada que no permite obtener un dibujo útil."""


@dataclass
class Drawing:
    cropped: Image.Image
    isolated: Image.Image
    ink: np.ndarray
    silhouette: np.ndarray
    bbox: tuple[int, int, int, int]
    source_size: tuple[int, int]
    processed_size: tuple[int, int]
    colors: list[dict]
    has_color: bool
    warnings: list[str]


def load_image(path: str | Path) -> Image.Image:
    path = Path(path)
    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        raise DrawingError("Usá una imagen JPG, PNG, WebP o HEIC.")
    if path.stat().st_size > 30 * 1024 * 1024:
        raise DrawingError("La imagen supera 30 MB. Reducila antes de cargarla.")
    try:
        with Image.open(path) as opened:
            if opened.width * opened.height > 40_000_000:
                raise DrawingError("La imagen supera 40 megapíxeles.")
            image = ImageOps.exif_transpose(opened)
            if image.mode in {"RGBA", "LA", "P"}:
                rgba = image.convert("RGBA")
                paper = Image.new("RGBA", rgba.size, "white")
                image = Image.alpha_composite(paper, rgba)
            return image.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise DrawingError("No pude leer esa imagen. Probá con otro archivo.") from exc


def _paper_crop(rgb: np.ndarray) -> tuple[np.ndarray, tuple[int, int]]:
    """Si se ve el borde de la hoja, quitar la mesa sin deformar el dibujo."""
    h, w = rgb.shape[:2]
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    light = ((hsv[:, :, 2] > 155) & (hsv[:, :, 1] < 75)).astype(np.uint8) * 255
    light = cv2.morphologyEx(light, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
    contours, _ = cv2.findContours(light, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        x, y, pw, ph = cv2.boundingRect(largest)
        coverage = cv2.contourArea(largest) / (h * w)
        # No recortar un parche pequeño claro ni cortar el dibujo al borde.
        if 0.40 < coverage < 0.94 and pw > w * 0.55 and ph > h * 0.55:
            inset = max(2, round(min(pw, ph) * 0.012))
            return rgb[y + inset:y + ph - inset, x + inset:x + pw - inset], (x + inset, y + inset)
    return rgb, (0, 0)


def _normalize_paper(rgb: np.ndarray) -> np.ndarray:
    """Estimar iluminación local; recuperar el blanco sin borrar lápiz tenue."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    # Ventana mayor que las zonas rellenas del personaje. Una ventana pequeña
    # confunde el interior coloreado con papel oscuro y blanquea sus colores.
    kernel_size = max(15, round(min(gray.shape) / 2) | 1)
    background = cv2.dilate(gray, np.ones((kernel_size, kernel_size), np.uint8))
    background = cv2.GaussianBlur(background, (0, 0), max(3, kernel_size / 8))
    gain = 255.0 / np.maximum(background.astype(np.float32), 80)
    return np.clip(rgb.astype(np.float32) * gain[:, :, None], 0, 255).astype(np.uint8)


def _group_components(mask: np.ndarray) -> np.ndarray:
    """Agrupar partes cercanas antes de seleccionar el personaje principal."""
    h, w = mask.shape
    # La dilatación solo decide qué partes pertenecen al personaje. El output
    # conserva los trazos originales y no sus versiones engrosadas.
    radius = max(3, round(min(h, w) * 0.018))
    grouping = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius * 2 + 1,) * 2))
    count, labels, stats, centers = cv2.connectedComponentsWithStats(grouping)
    if count <= 1:
        raise DrawingError("No encontré trazos. Probá una foto más cercana y con mejor luz.")
    scores = []
    for label in range(1, count):
        x, y, cw, ch, _ = stats[label]
        original_area = np.count_nonzero(mask[labels == label])
        cx, cy = centers[label]
        distance = np.hypot((cx - w / 2) / w, (cy - h / 2) / h)
        border_penalty = 0.25 if (x == 0 or y == 0 or x + cw >= w or y + ch >= h) else 1
        scores.append(original_area * (1 - min(distance, 0.7)) * border_penalty)
    main = int(np.argmax(scores)) + 1
    chosen = labels == main
    x, y, cw, ch, _ = stats[main]
    # Conservar ojos/orejas/accesorios separados cerca del conjunto principal.
    margin = max(8, round(max(cw, ch) * 0.12))
    for label in range(1, count):
        cx, cy = centers[label]
        if x - margin <= cx <= x + cw + margin and y - margin <= cy <= y + ch + margin:
            chosen |= labels == label
    selected = np.where(chosen, mask, 0).astype(np.uint8)
    area = np.count_nonzero(selected)
    if area < max(35, h * w * 0.00035):
        raise DrawingError("El dibujo es demasiado tenue o pequeño. Acercá la cámara al personaje.")
    return selected


def _fill_enclosed(mask: np.ndarray) -> np.ndarray:
    """Rellenar interiores cerrados, sin rellenar todo el rectángulo del recorte."""
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    padded = cv2.copyMakeBorder(closed, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    flood = padded.copy()
    cv2.floodFill(flood, None, (0, 0), 255)
    filled = padded | cv2.bitwise_not(flood)
    return filled[1:-1, 1:-1]


def dominant_colors(rgb: np.ndarray, foreground: np.ndarray) -> tuple[list[dict], bool]:
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    valid = (foreground > 0) & (hsv[:, :, 1] > 45) & (hsv[:, :, 2] > 55)
    pixels = rgb[valid]
    foreground_count = max(1, np.count_nonzero(foreground))
    colored = len(pixels) >= max(20, foreground_count * 0.015)
    if not colored:
        return [], False
    # Cuantización determinista: evita que el RNG global cambie entre threads.
    bins = (pixels.astype(np.int32) // 32)
    keys = bins[:, 0] * 64 + bins[:, 1] * 8 + bins[:, 2]
    values, counts = np.unique(keys, return_counts=True)
    order = np.argsort(-counts, kind="stable")
    colors = []
    for index in order:
        if counts[index] / len(pixels) < 0.025:
            continue
        color = np.median(pixels[keys == values[index]], axis=0).astype(int)
        if any(np.linalg.norm(color - np.array(item["rgb"])) < 48 for item in colors):
            continue
        colors.append({
            "hex": "#" + "".join(f"{c:02X}" for c in color),
            "rgb": color.tolist(),
            "fraction": round(float(counts[index] / len(pixels)), 4),
        })
        if len(colors) == 5:
            break
    return colors, bool(colors)


def preprocess(image: Image.Image) -> Drawing:
    source_size = image.size
    working = image.copy()
    working.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
    rgb, offset = _paper_crop(np.array(working))
    cleaned = _normalize_paper(rgb)
    gray = cv2.cvtColor(cleaned, cv2.COLOR_RGB2GRAY)
    hsv = cv2.cvtColor(cleaned, cv2.COLOR_RGB2HSV)
    # Contraste local + color: los lápices amarillos no dependen de ser oscuros.
    local = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                  cv2.THRESH_BINARY_INV, 35, 9)
    ink = ((gray < 180) | ((local > 0) & (gray < 242)) |
           (hsv[:, :, 1] > 45))
    ink = ink.astype(np.uint8) * 255
    # Filtrar puntitos de ruido; conservar los ojos pequeños.
    count, labels, stats, _ = cv2.connectedComponentsWithStats(ink)
    minimum = max(3, round(ink.size * 0.000004))
    keep = np.zeros(count, dtype=np.uint8)
    keep[1:] = np.where(stats[1:, cv2.CC_STAT_AREA] >= minimum, 255, 0)
    ink = _group_components(keep[labels])
    points = cv2.findNonZero(ink)
    x, y, w, h = cv2.boundingRect(points)
    margin = max(12, round(max(w, h) * 0.07))
    left, top = max(0, x - margin), max(0, y - margin)
    right, bottom = min(rgb.shape[1], x + w + margin), min(rgb.shape[0], y + h + margin)
    crop = cleaned[top:bottom, left:right]
    strokes = ink[top:bottom, left:right]
    silhouette = _fill_enclosed(strokes)
    colors, has_color = dominant_colors(crop, silhouette)
    # Mantener interiores blancos opacos: papel exterior sí, ojos blancos no.
    isolated_rgb = np.where(silhouette[:, :, None] > 0, crop, 255).astype(np.uint8)
    isolated = Image.fromarray(np.dstack([isolated_rgb, silhouette]))
    warnings = []
    if np.count_nonzero(silhouette) / silhouette.size < 0.06:
        warnings.append("El contorno está abierto o es tenue; la silueta puede ser aproximada.")
    ox, oy = offset
    scale_x = source_size[0] / working.width
    scale_y = source_size[1] / working.height
    bbox = (round((left + ox) * scale_x), round((top + oy) * scale_y),
            round((right + ox) * scale_x), round((bottom + oy) * scale_y))
    return Drawing(Image.fromarray(crop), isolated, strokes, silhouette, bbox,
                   source_size, working.size, colors, has_color, warnings)


def color_name(hex_color: str) -> str:
    """Nombres ingleses utilizables por CLIP, que no interpreta códigos HEX."""
    references = {
        "red": (220, 60, 65), "coral": (245, 145, 135), "orange": (235, 150, 45),
        "yellow": (245, 215, 80), "cream": (255, 226, 168), "green": (60, 165, 80),
        "mint green": (145, 205, 181), "teal": (55, 170, 170), "blue": (65, 120, 220),
        "light blue": (150, 205, 240), "purple": (155, 95, 200), "pink": (243, 154, 168),
        "brown": (135, 90, 55), "gray": (155, 155, 155), "black": (35, 35, 35),
    }
    rgb = np.array([int(hex_color[i:i + 2], 16) for i in (1, 3, 5)])
    return min(references, key=lambda name: np.linalg.norm(rgb - np.array(references[name])))


def make_references(drawing: Drawing, size: int, palette: list[str],
                    preserve_colors: bool) -> tuple[Image.Image, Image.Image]:
    rgb = np.array(drawing.isolated.convert("RGB"))
    if not preserve_colors:
        # Quitar también el color original cuando se fuerza la paleta.
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        rgb = np.repeat(gray[:, :, None], 3, axis=2)
        fill = (drawing.silhouette > 0) & (gray > 135)
        primary = np.array([int(palette[0][i:i + 2], 16) for i in (1, 3, 5)])
        rgb[fill] = primary
    rgb[drawing.silhouette == 0] = 255
    # Scribble espera trazos blancos sobre negro. Incluir bordes de áreas
    # coloreadas, pero no convertir toda un área rellena en un trazo sólido.
    edges = cv2.Canny(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY), 55, 140)
    dark = (cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY) < 125).astype(np.uint8) * 255
    thin = cv2.morphologyEx(dark, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
    scribble = cv2.bitwise_or(edges, thin)
    scribble[drawing.silhouette == 0] = 0
    reference = ImageOps.contain(Image.fromarray(rgb), (int(size * 0.84),) * 2)
    control = Image.fromarray(scribble).resize(reference.size, Image.Resampling.NEAREST)
    canvas = Image.new("RGB", (size, size), "white")
    condition = Image.new("RGB", (size, size), "black")
    position = ((size - reference.width) // 2, (size - reference.height) // 2)
    canvas.paste(reference, position)
    condition.paste(control.convert("RGB"), position)
    return canvas, condition
