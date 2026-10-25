"""Reconocimiento geométrico de la hoja de demo y transferencia local de color."""

from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from .config import ROOT
from .processing import Drawing, DrawingError, _normalize_paper, _fill_enclosed, dominant_colors, preprocess
from .rig import Puppet, RigError, SPECIES, composite, load_puppet, make_guide, recolor

DEMO_DIR = ROOT / "assets" / "demo" / "stitch"
ROLES = ("primary", "secondary", "accent")


def demo_ready(directory: Path = DEMO_DIR) -> bool:
    try:
        puppet = load_puppet(directory, require_generated=False)
        _reference(directory)
        return puppet.manifest.get("id") == "stitch-demo" and puppet.manifest.get("provenance", {}).get("status") == "prepared"
    except (RigError, OSError, ValueError):
        return False


def outline_image(image: Image.Image) -> np.ndarray:
    # Max RGB descarta lápices de color: se comparan los trazos negros impresos.
    rgb = _normalize_paper(np.array(image.convert("RGB")))
    return np.where(rgb.max(axis=2) < 125, 0, 255).astype(np.uint8)


@lru_cache(maxsize=1)
def _reference(directory: Path):
    with Image.open(directory / "reference.png") as image:
        reference = np.array(image.convert("L"))
    points, descriptors = cv2.SIFT_create(nfeatures=1600, contrastThreshold=.025).detectAndCompute(reference, None)
    masks = {}
    for role in ROLES:
        with Image.open(directory / f"region_{role}.png") as image:
            masks[role] = np.array(image.convert("L"))
    return reference, points, descriptors, masks


@dataclass
class DemoMatch:
    aligned: Image.Image
    colors: dict[str, str]
    evidence: dict


def _recognize_exact(image: Image.Image, directory: Path) -> DemoMatch | None:
    if not (directory / "character.json").is_file() or not (directory / "reference.png").is_file():
        return None
    reference, reference_points, descriptors, masks = _reference(directory)
    working = image.copy()
    working.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
    points, observed = cv2.SIFT_create(nfeatures=2400, contrastThreshold=.025).detectAndCompute(outline_image(working), None)
    if observed is None or len(observed) < 2 or descriptors is None:
        return None
    pairs = cv2.BFMatcher().knnMatch(descriptors, observed, k=2)
    good = [a for pair in pairs if len(pair) == 2 for a, b in [pair] if a.distance < .7 * b.distance]
    if len(good) < 14:
        return None
    src = np.float32([reference_points[m.queryIdx].pt for m in good])
    dst = np.float32([points[m.trainIdx].pt for m in good])
    homography, active = cv2.findHomography(src, dst, cv2.RANSAC, 4.0)
    if homography is None or active is None:
        return None
    inliers = active.ravel().astype(bool)
    count, ratio = int(inliers.sum()), float(inliers.mean())
    h, w = reference.shape
    # Distribución espacial: una coincidencia aislada de ojos o dientes no alcanza.
    hull_area = cv2.contourArea(cv2.convexHull(src[inliers])) / (w * h)
    if count < 12 or ratio < .48 or hull_area < .12:
        return None
    corners = np.float32([[[0, 0], [w, 0], [w, h], [0, h]]])
    projected = cv2.perspectiveTransform(corners, homography)[0]
    area = cv2.contourArea(projected, oriented=True)
    if (not np.isfinite(projected).all() or not cv2.isContourConvex(projected)
            or area < working.width * working.height * .035 or area > working.width * working.height * 1.35
            or projected[:, 0].min() < -working.width * .2 or projected[:, 0].max() > working.width * 1.2
            or projected[:, 1].min() < -working.height * .2 or projected[:, 1].max() > working.height * 1.2):
        return None
    aligned = cv2.warpPerspective(np.array(working), np.linalg.inv(homography), (w, h), borderValue=(255, 255, 255))
    cleaned = _normalize_paper(aligned)
    colors = {}
    for role, mask in masks.items():
        detected, colored = dominant_colors(cleaned, mask)
        if colored:
            colors[role] = detected[0]["hex"]
    return DemoMatch(Image.fromarray(cleaned), colors, {
        "id": "stitch-demo", "method": "sift_outline_homography", "matches": len(good),
        "inliers": count, "inlier_ratio": round(ratio, 4), "reference_coverage": round(hull_area, 4),
        "region_colors": colors, "homography": homography.tolist(), "working_size": list(working.size),
    })


def _shape_mask(mask: np.ndarray):
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    main = max(contours, key=cv2.contourArea)
    if cv2.contourArea(main) < mask.size * .04:
        return None
    x, y, w, h = cv2.boundingRect(main)
    filled = np.zeros_like(mask)
    cv2.drawContours(filled, [main], -1, 255, cv2.FILLED)
    normalized = cv2.resize(filled[y:y+h, x:x+w], (192, 192), interpolation=cv2.INTER_NEAREST)
    return normalized > 0, (x, y, w, h)


@lru_cache(maxsize=1)
def _shape_references(directory: Path):
    reference, *_ = _reference(directory)
    hand = _shape_mask(_fill_enclosed(255 - reference))
    prepared = _shape_mask(np.array(composite(load_puppet(directory, require_generated=False)).getchannel("A")))
    others = [_shape_mask(np.array(composite(make_guide(species)).getchannel("A")))[0] for species in SPECIES]
    return hand, prepared, others


def _overlap(a, b):
    return np.count_nonzero(a & b) / max(1, np.count_nonzero(a | b))


def _recognize_shape(image: Image.Image, drawing: Drawing, directory: Path) -> DemoMatch | None:
    hand, prepared, others = _shape_references(directory)
    best = None
    # El dibujo puede rehacerse, inclinarse y cambiar de proporciones. Comparar
    # la silueta completa normalizada, sin exigir coincidencias de cada trazo.
    height, width = drawing.silhouette.shape
    diagonal = int(np.hypot(width, height)) + 4
    source_center = np.array([width / 2, height / 2])
    for degrees in range(-18, 19, 3):
        matrix = cv2.getRotationMatrix2D(tuple(source_center), degrees, 1)
        matrix[:, 2] += (diagonal / 2 - source_center)
        rotated = cv2.warpAffine(drawing.silhouette, matrix, (diagonal, diagonal))
        candidate = _shape_mask(rotated)
        if candidate is None:
            continue
        mask, bounds = candidate
        score = max(_overlap(mask, hand[0]), _overlap(mask, prepared[0]))
        competitor = max(_overlap(mask, other) for other in others)
        if best is None or score > best[0]:
            best = score, competitor, bounds, matrix, degrees
    if best is None or best[0] < .76 or best[0] - best[1] < .07:
        return None
    score, competitor, (x, y, w, h), rotation, degrees = best
    # Llevar regiones de la foto a la referencia; conservar el rig ya preparado.
    rx, ry, rw, rh = hand[1]
    fit = np.array([[rw / w, 0, rx - x * rw / w], [0, rh / h, ry - y * rh / h], [0, 0, 1]])
    photo_to_reference = fit @ np.vstack([rotation, [0, 0, 1]])
    reference, _, _, regions = _reference(directory)
    aligned = cv2.warpPerspective(np.array(drawing.isolated.convert("RGB")), photo_to_reference,
                                  (reference.shape[1], reference.shape[0]), borderValue=(255, 255, 255))
    # Erosión de pigmento cromático: un borde de birome no pinta toda la piel.
    hsv = cv2.cvtColor(aligned, cv2.COLOR_RGB2HSV)
    colored = ((hsv[:, :, 1] > 45) & (hsv[:, :, 2] > 55)).astype(np.uint8) * 255
    broad_color = cv2.morphologyEx(colored, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    colors = {}
    for role, region in regions.items():
        interior = cv2.erode(region, np.ones((5, 5), np.uint8))
        eligible = cv2.bitwise_and(interior, broad_color)
        if np.count_nonzero(eligible) < max(30, np.count_nonzero(interior) * .08):
            continue
        detected, has_color = dominant_colors(aligned, eligible)
        if has_color:
            colors[role] = detected[0]["hex"]
    return DemoMatch(Image.fromarray(aligned), colors, {
        "id": "stitch-demo", "method": "silhouette_shape", "shape_overlap": round(score, 4),
        "other_species_overlap": round(competitor, 4), "rotation_degrees": degrees,
        "region_colors": colors, "photo_to_reference": photo_to_reference.tolist(),
        "alignment_coordinates": "isolated drawing crop pixels", "live_model_inference": False,
    })


def recognize_demo(image: Image.Image, directory: Path = DEMO_DIR, *, drawing: Drawing | None = None) -> DemoMatch | None:
    if not (directory / "character.json").is_file() or not (directory / "reference.png").is_file():
        return None
    exact = _recognize_exact(image, directory)
    if exact is not None:
        return exact
    try:
        return _recognize_shape(image, drawing or preprocess(image), directory)
    except DrawingError:
        return None


def personalize_demo(match: DemoMatch, palette: list[str], preserve_colors: bool,
                     directory: Path = DEMO_DIR) -> Puppet:
    base = load_puppet(directory, require_generated=False)
    if base.manifest.get("id") != "stitch-demo" or base.manifest.get("provenance", {}).get("status") != "prepared":
        raise ValueError("El personaje de demo no está preparado.")
    colors = dict(zip(ROLES, palette))
    if preserve_colors:
        # Papel sin pintar queda claro; no inventar colores en zonas vacías.
        colors = {role: match.colors.get(role, "#F5F3F0") for role in ROLES}
    puppet = Puppet(deepcopy(base.manifest), dict(base.textures))
    for layer in puppet.manifest["layers"]:
        role = layer.get("color_role")
        if role:
            puppet.textures[layer["id"]] = recolor(puppet.textures[layer["id"]], colors[role])
    puppet.manifest.update({"palette": [colors[role] for role in ROLES], "base_id": "stitch-demo",
                            "base_provenance": base.manifest["provenance"]})
    puppet.manifest["provenance"] = {"status": "prepared", "operation": "recolor_demo",
                                      "method": "registered_photo_region_colors", "recognition": match.evidence,
                                      "live_model_inference": False}
    return puppet
