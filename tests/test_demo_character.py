"""Fotos de la misma hoja pintada, cambios de cámara y aislamiento del camino rápido."""

from dataclasses import replace
import json
import zipfile

import cv2
import numpy as np
from PIL import Image, ImageDraw
import pytest

from draw_to_life.config import ROOT, Settings
from draw_to_life.demo_character import DEMO_DIR, demo_ready, recognize_demo
from draw_to_life.pipeline import Pipeline
from draw_to_life.rig import composite, load_puppet, make_guide


def colored_sheet(colored=True):
    with Image.open(DEMO_DIR / "reference.png") as reference:
        ink = np.array(reference.convert("L")) < 128
        rgb = np.full((*ink.shape, 3), 247, np.uint8)
    if colored:
        for role, color in {"primary": (80, 160, 225), "secondary": (250, 200, 65), "accent": (220, 100, 165)}.items():
            with Image.open(DEMO_DIR / f"region_{role}.png") as mask:
                rgb[np.array(mask) > 0] = color
    rgb[ink] = (25, 24, 28)
    return Image.fromarray(rgb)


def photograph(sheet):
    # Nueva perspectiva, escala, fondo, sombra gradual y compresión de cámara.
    w, h = sheet.size
    source = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    target = np.float32([[170, 120], [850, 175], [910, 900], [105, 850]])
    transform = cv2.getPerspectiveTransform(source, target)
    rgb = cv2.warpPerspective(np.array(sheet), transform, (1050, 1050), borderValue=(95, 65, 40))
    rgb = np.clip(rgb * np.linspace(.78, 1.0, 1050)[None, :, None], 0, 255).astype(np.uint8)
    return Image.fromarray(cv2.GaussianBlur(rgb, (3, 3), .5))


@pytest.mark.parametrize("transform", [lambda image: image, photograph, lambda image: image.rotate(16, expand=True, fillcolor="white")])
def test_recognizes_repainted_contour_and_region_colors(transform):
    match = recognize_demo(transform(colored_sheet()))
    assert match is not None
    assert match.evidence["inliers"] >= 12
    for role, channel in [("primary", 2), ("secondary", 0), ("accent", 0)]:
        color = match.colors[role]
        values = [int(color[i:i+2], 16) for i in (1, 3, 5)]
        assert values[channel] == max(values)
    assert match.colors["primary"] != match.colors["accent"]


@pytest.mark.parametrize("image", [Image.new("RGB", (700, 900), "white"),
                                   composite(make_guide("rabbit"), background="white").convert("RGB"),
                                   composite(make_guide("cat"), background="white").convert("RGB")])
def test_unrelated_images_never_use_demo(image):
    assert recognize_demo(image) is None


def test_matching_just_the_face_is_insufficient():
    face = colored_sheet().crop((220, 240, 580, 455)).resize((760, 750))
    assert recognize_demo(face) is None


def test_background_does_not_change_palette():
    sheet = colored_sheet()
    first = recognize_demo(sheet)
    canvas = Image.new("RGB", (1100, 1000), "#38CB48")
    canvas.paste(sheet, (170, 100))
    ImageDraw.Draw(canvas).rectangle((0, 0, 1100, 55), fill="#ED7A12")
    second = recognize_demo(canvas)
    assert second is not None
    assert second.colors == first.colors


@pytest.mark.parametrize("colored,color_mode", [(True, "Colores del dibujo"), (False, "Colores del dibujo"), (True, "Paleta por defecto")])
def test_complete_fast_path_never_loads_models(tmp_path, monkeypatch, colored, color_mode):
    settings = replace(Settings.from_env(), output_dir=tmp_path / "runs", catalog_dir=tmp_path / "absent-catalog")
    pipeline = Pipeline(settings)
    def forbidden(*_args, **_kwargs):
        pytest.fail("La ruta de demo no debe cargar visión ni difusión")
    monkeypatch.setattr("draw_to_life.pipeline.local_models", forbidden)
    monkeypatch.setattr("draw_to_life.pipeline.describe", forbidden)
    monkeypatch.setattr(pipeline.characters, "adapt", forbidden)
    monkeypatch.setattr(pipeline.characters, "generate_parts", forbidden)
    monkeypatch.setattr(pipeline.generator, "generate", forbidden)
    photo = tmp_path / "camera.png"
    photograph(colored_sheet(colored)).save(photo)
    run = pipeline.prepare(photo, "Cartoon infantil", color_mode, list(settings.palette), mode="auto")
    assert run.demo_match is not None
    assert pipeline.finish(run).is_file()
    metadata = json.loads((run.directory / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "completed"
    assert metadata["generation_mode"] == "prepared_demo"
    assert not metadata["live_model_inference"] and metadata["models"] == {}
    assert metadata["generation_seconds"] == 0
    exported = load_puppet(run.directory / "character", require_generated=False)
    assert exported.manifest["base_id"] == "stitch-demo"
    for layer in exported.manifest["layers"]:
        if layer.get("motion") in {"blink", "smile"}:
            assert layer["expressions"]
    if color_mode == "Paleta por defecto":
        assert exported.manifest["palette"] == list(settings.palette)
    elif not colored:
        assert exported.manifest["palette"] == ["#F5F3F0"] * 3
    else:
        assert len(set(exported.manifest["palette"])) == 3
    with zipfile.ZipFile(run.directory / "character.zip") as bundle:
        assert {"index.html", "character.json", "character-player.js"} <= set(bundle.namelist())


@pytest.mark.parametrize("mode,animal", [("free", None), ("template", None), ("auto", "rabbit"), ("legacy", None)])
def test_explicit_modes_and_species_keep_their_behavior(tmp_path, mode, animal):
    source = tmp_path / "source.png"
    colored_sheet().save(source)
    settings = replace(Settings.from_env(), output_dir=tmp_path / "runs")
    run = Pipeline(settings).prepare(source, "Cartoon infantil", "Colores del dibujo", list(settings.palette), mode=mode, animal=animal)
    assert run.demo_match is None


def test_packaged_demo_is_ready_and_other_drawing_is_not_it():
    assert demo_ready()
    with Image.open(ROOT / "test1.png") as image:
        assert recognize_demo(image.convert("RGB")) is None
