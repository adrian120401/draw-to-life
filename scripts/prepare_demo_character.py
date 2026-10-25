"""Preparar el rig de la demo y su referencia de contorno, sin inferencia en vivo."""

import argparse
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from draw_to_life.config import ROOT  # noqa: E402
from draw_to_life.demo_character import outline_image  # noqa: E402
from draw_to_life.expressions import with_expressions  # noqa: E402
from draw_to_life.processing import load_image  # noqa: E402
from draw_to_life.rig import Puppet, _shaded, export_package  # noqa: E402


def build_puppet():
    """Arte vectorial propio por piezas: orejas, brazos, pies, cara y pancita."""
    size, supersample = 512, 3
    layers, textures = [], {}
    palette = ["#F39AA8", "#F9D3DB", "#C9698C"]

    def piece(name, parent, pivot, role, commands, motion="", color=None):
        points = []
        for command in commands:
            if len(command) == 2:
                points.append(np.array(command, dtype=float))
            else:
                start = points[-1]
                a, b, end = np.array(command).reshape(3, 2)
                for t in np.linspace(0, 1, 26)[1:]:
                    points.append((1-t)**3*start + 3*(1-t)**2*t*a + 3*(1-t)*t*t*b + t**3*end)
        mask = Image.new("L", (size * supersample,) * 2)
        ImageDraw.Draw(mask).polygon([tuple(p * supersample) for p in points], fill=255)
        mask = mask.resize((size, size), Image.Resampling.LANCZOS)
        textures[name] = _shaded(mask, color or palette[{"primary": 0, "secondary": 1, "accent": 2}.get(role, 0)])
        layers.append({"id": name, "parent": parent, "pivot": list(pivot),
                       "texture": f"textures/{name}.png", "color_role": role,
                       "motion": motion, "generated": False})

    piece("arm_left", "body", (205, 326), "primary", [
        (213, 314), (178, 313, 147, 302, 122, 307), (89, 299), (103, 317),
        (76, 326), (96, 336), (82, 348), (103, 349), (102, 367),
        (120, 356), (132, 377, 174, 365, 211, 341)], "sway")
    piece("arm_right", "body", (312, 325), "primary", [
        (302, 314), (346, 312, 391, 286, 449, 272), (437, 297),
        (464, 293), (443, 315), (461, 322), (443, 334), (456, 350),
        (418, 341), (390, 341, 349, 351, 310, 344)], "sway")
    piece("foot_left", "body", (225, 423), "primary", [
        (205, 396), (184, 410, 180, 434, 171, 448), (184, 448), (186, 462),
        (205, 454), (228, 468), (234, 451), (255, 448), (256, 417)])
    piece("foot_right", "body", (295, 423), "primary", [
        (270, 410), (272, 439, 287, 451, 303, 449), (317, 456), (328, 446),
        (344, 450), (346, 438), (363, 434), (345, 416), (349, 388, 325, 380, 310, 388)])
    piece("body", None, (262, 441), "primary", [
        (212, 290), (191, 327, 201, 355, 193, 389), (187, 420, 213, 434, 251, 426),
        (277, 421, 302, 440, 327, 407), (346, 368, 316, 319, 304, 291)], "breathe")
    piece("belly", "body", (262, 379), "secondary", [
        (235, 314), (213, 344, 216, 389, 233, 402), (249, 410, 280, 407, 294, 394),
        (318, 372, 296, 326, 283, 316), (265, 329, 251, 327, 235, 314)])
    piece("ear_left", "head", (162, 229), "primary", [
        (172, 252), (142, 217, 133, 191, 129, 160), (124, 129, 126, 85, 103, 77),
        (81, 67, 70, 91, 80, 117), (44, 128, 54, 177, 70, 207),
        (83, 233, 96, 247, 118, 248), (148, 259), (126, 272), (164, 265)], "sway")
    piece("ear_inner_left", "ear_left", (115, 185), "accent", [
        (101, 96), (110, 116, 110, 146, 117, 171), (124, 204, 133, 227, 142, 242),
        (111, 235), (81, 208, 66, 153, 84, 140), (98, 132, 96, 115, 101, 96)])
    piece("ear_right", "head", (361, 230), "primary", [
        (353, 256), (365, 211, 365, 172, 371, 133), (367, 99, 365, 55, 387, 47),
        (408, 36, 425, 77, 439, 110), (449, 137, 446, 166, 445, 187),
        (438, 199, 425, 198, 416, 202), (429, 214), (412, 229), (391, 234), (388, 253)], "sway")
    piece("ear_inner_right", "ear_right", (399, 151), "accent", [
        (386, 66), (400, 60, 427, 116, 431, 143), (434, 163, 432, 180, 431, 186),
        (405, 191), (412, 210), (394, 214), (380, 228), (384, 173, 382, 116, 386, 66)])
    piece("head", "body", (260, 307), "primary", [
        (145, 248), (140, 217, 155, 186, 179, 174), (197, 160, 206, 157, 205, 143),
        (218, 148), (233, 143), (227, 158), (270, 155, 337, 174, 353, 199),
        (377, 216, 385, 250, 368, 277), (351, 304, 311, 321, 267, 321),
        (220, 327, 168, 310, 153, 282), (148, 268, 145, 259, 145, 248)], "head")
    for name, commands in [
        ("patch_left", [(169, 199), (188, 180, 223, 210, 239, 238), (244, 261, 228, 284, 201, 280), (166, 274, 149, 224, 169, 199)]),
        ("patch_right", [(311, 184), (332, 178, 357, 201, 359, 231), (356, 258, 338, 275, 313, 268), (294, 252, 296, 209, 311, 184)]),
    ]:
        piece(name, "head", (260, 240), "secondary", commands)
    for name, box in [("eye_left", (177, 224, 228, 280)), ("eye_right", (315, 206, 353, 262))]:
        texture = Image.new("RGBA", (size * supersample,) * 2)
        draw = ImageDraw.Draw(texture)
        draw.ellipse(tuple(v * supersample for v in box), fill="#222333")
        x, y, r, b = box
        draw.ellipse(((x+7)*3, (y+6)*3, (r-13)*3, (y+20)*3), fill="#FFF9EE")
        draw.ellipse(((r-13)*3, (b-13)*3, (r-7)*3, (b-7)*3), fill="#A8C6D5")
        textures[name] = texture.resize((size, size), Image.Resampling.LANCZOS)
        layers.append({"id": name, "parent": "head", "pivot": [(x+r)/2, (y+b)/2],
                       "texture": f"textures/{name}.png", "color_role": None, "motion": "blink", "generated": False})
    piece("nose", "head", (270, 257), "accent", [
        (238, 242), (252, 237, 278, 232, 294, 240), (308, 247, 296, 270, 277, 280),
        (261, 283, 245, 269, 238, 257), (232, 252, 234, 248, 238, 242)])
    piece("mouth", "head", (268, 291), None, [
        (183, 286), (230, 300, 305, 300, 343, 278), (319, 313, 228, 338, 183, 286)], "smile", "#292539")
    # Dientes separados por líneas oscuras; la sonrisa es una pieza animable.
    mouth_alpha = textures["mouth"].getchannel("A")
    draw = ImageDraw.Draw(textures["mouth"])
    draw.polygon([(198, 292), (220, 298), (226, 308), (212, 305)], fill="#FFF9EE")
    for x in range(230, 316, 16):
        draw.polygon([(x, 299), (x+10, 298), (x+13, 309), (x+3, 312)], fill="#FFF9EE")
    textures["mouth"].putalpha(mouth_alpha)
    manifest = {"schema_version": 1, "id": "stitch-demo", "name": "Stitch", "species": "stitch",
                "creature": "Stitch with long notched ears and a wide toothy smile", "canvas": [size, size],
                "palette": palette, "layers": layers, "face_bounds": [155, 180, 365, 320],
                "animations": {"idle": {"duration": 3.2, "loop": True, "breath_scale": .018, "head_degrees": 1.5},
                               "blink": {"duration": .18, "interval": 4.3},
                               "react": {"duration": .85, "jump": .025, "tilt_degrees": 8}},
                "provenance": {"status": "prepared", "method": "authored_vector_rig", "operation": "prepare_demo",
                               "source": "User-provided demo drawing; manually authored geometry, no live diffusion."}}
    return with_expressions(Puppet(manifest, textures))


def prepare(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    # Solo se guarda el contorno del personaje, sin mesa, personas ni metadatos EXIF.
    crop = load_image(source).crop((40, 450, 800, 1200))
    Image.fromarray(outline_image(crop)).save(destination / "reference.png")
    regions = {
        "primary": [[(350, 658), (430, 660), (494, 684), (483, 718), (404, 741), (366, 710)],
                    [(285, 973), (310, 966), (301, 1030), (291, 1063), (278, 1084)],
                    [(621, 855), (713, 829), (724, 869), (707, 887), (626, 887)]],
        "secondary": [[(374, 940), (444, 934), (474, 992), (475, 1035), (446, 1051), (383, 1050), (363, 1010)]],
        "accent": [[(117, 645), (155, 627), (171, 721), (201, 807), (148, 808), (106, 719)],
                   [(624, 499), (650, 500), (692, 561), (707, 620), (703, 703), (656, 718), (647, 748), (628, 666)]]}
    for role, polygons in regions.items():
        mask = Image.new("L", crop.size)
        draw = ImageDraw.Draw(mask)
        for polygon in polygons:
            draw.polygon([(x-40, y-450) for x, y in polygon], fill=255)
        mask.save(destination / f"region_{role}.png")
    archive = export_package(build_puppet(), destination)
    archive.replace(destination.with_suffix(".zip"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Foto de referencia original (900×1600)")
    args = parser.parse_args()
    prepare(args.source, ROOT / "assets" / "demo" / "stitch")
