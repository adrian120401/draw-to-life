"""Regresiones de papel texturado y del Stitch redibujado de la demo."""

from pathlib import Path
from dataclasses import replace

import cv2
import numpy as np
from PIL import Image, ImageDraw
import pytest

from draw_to_life.demo_character import recognize_demo
from draw_to_life.config import Settings
from draw_to_life.pipeline import Pipeline
from draw_to_life.processing import DrawingError, load_image, preprocess

REDRAWN = Path(__file__).parent / "fixtures" / "stitch-redrawn.jpg"


def test_real_photo_discards_paper_grain_and_preserves_character():
    drawing = preprocess(load_image(REDRAWN))
    assert drawing.bbox[1] > 100  # La textura del papel no extiende el dibujo hasta arriba.
    alpha = np.array(drawing.isolated.getchannel("A"))
    assert np.count_nonzero(alpha) / alpha.size < .70
    assert np.count_nonzero(alpha[:20]) == 0
    # La hoja se blanquea incluso dentro del personaje; sus interiores siguen opacos.
    rgba = np.array(drawing.isolated)
    assert np.count_nonzero((rgba[:, :, :3].min(axis=2) > 245) & (alpha == 255)) > 5000


def test_redrawn_character_uses_the_prepared_rig():
    match = recognize_demo(load_image(REDRAWN))
    assert match is not None
    assert match.evidence["method"] == "silhouette_shape"
    assert not match.colors  # El trazo de birome azul no es pintura del cuerpo.


@pytest.mark.parametrize("angle", [-12, 12])
def test_rotated_redrawn_character_is_recognized(angle):
    photo = load_image(REDRAWN).rotate(angle, expand=True, fillcolor="#F5F4EF")
    match = recognize_demo(photo)
    assert match is not None and match.evidence["method"] == "silhouette_shape"


def painted_redrawing():
    photo = load_image(REDRAWN)
    colors = {"primary": "#4BA6D9", "secondary": "#F1C64A", "accent": "#EA7EAF"}
    polygons = {
        "primary": [(425, 450), (570, 470), (670, 510), (620, 545), (490, 563), (365, 550), (360, 510)],
        "secondary": [(450, 875), (510, 870), (550, 927), (550, 970), (490, 985), (440, 965)],
        "accent": [(90, 420), (130, 430), (170, 550), (210, 680), (130, 600), (70, 530)]}
    painted = photo.copy()
    draw = ImageDraw.Draw(painted)
    for role, polygon in polygons.items():
        draw.polygon(polygon, fill=colors[role])
    # Dejar intactos los trazos oscuros originales al simular lápices sobre papel.
    rgb, original = np.array(painted), np.array(photo)
    rgb[original.max(axis=2) < 155] = original[original.max(axis=2) < 155]
    return Image.fromarray(rgb), colors


def test_paint_colors_transfer_from_the_redrawing():
    photo, expected = painted_redrawing()
    match = recognize_demo(photo)
    assert match is not None
    for role, color in expected.items():
        observed = [int(match.colors[role][i:i+2], 16) for i in (1, 3, 5)]
        wanted = [int(color[i:i+2], 16) for i in (1, 3, 5)]
        assert np.linalg.norm(np.array(observed) - wanted) < 45


def test_real_redrawing_pipeline_skips_vision_and_diffusion(tmp_path, monkeypatch):
    pipeline = Pipeline(replace(Settings.from_env(), output_dir=tmp_path / "runs"))
    def forbidden(*_args, **_kwargs):
        pytest.fail("El dibujo rehecho debe usar la ruta rápida")
    monkeypatch.setattr("draw_to_life.pipeline.local_models", forbidden)
    monkeypatch.setattr("draw_to_life.pipeline.describe", forbidden)
    run = pipeline.prepare(REDRAWN, "Cartoon infantil", "Colores del dibujo", list(pipeline.settings.palette), mode="auto")
    pipeline.finish(run)
    assert run.metadata["generation_mode"] == "prepared_demo"
    assert run.puppet.manifest["id"] == "stitch-demo"
    assert run.metadata["models"] == {} and not run.metadata["live_model_inference"]
    assert run.metadata["bounding_box_coordinates"].startswith("original image pixels")
    assert (run.directory / "character.zip").is_file()


def textured_paper():
    rng = np.random.default_rng(42)
    yy, xx = np.mgrid[:900, :700]
    gray = 238 - 48 * (xx / 700) + rng.normal(0, 6, (900, 700))
    return Image.fromarray(np.repeat(np.clip(gray, 0, 255).astype(np.uint8)[:, :, None], 3, axis=2))


def test_empty_shadowed_textured_paper_is_not_a_character():
    with pytest.raises(DrawingError, match="trazos|tenue"):
        preprocess(textured_paper())


def test_pencil_strokes_survive_paper_removal():
    paper = textured_paper()
    draw = ImageDraw.Draw(paper)
    draw.ellipse((180, 190, 520, 700), outline="#888888", width=5)
    draw.ellipse((250, 310, 275, 345), fill="#777777")
    draw.ellipse((410, 310, 435, 345), fill="#777777")
    drawing = preprocess(paper)
    assert 100 < drawing.bbox[1] < 195
    assert drawing.bbox[3] > 700
    assert not drawing.has_color


def test_tilted_paper_removes_the_table_corners():
    from scripts.make_examples import example
    paper = example("conejo").resize((490, 595))
    source = np.float32([[0, 0], [490, 0], [490, 595], [0, 595]])
    target = np.float32([[130, 90], [590, 145], [555, 755], [75, 710]])
    rgb = cv2.warpPerspective(np.array(paper), cv2.getPerspectiveTransform(source, target),
                               (700, 850), borderValue=(114, 86, 67))
    drawing = preprocess(Image.fromarray(rgb))
    assert drawing.bbox[1] > 120 and drawing.bbox[3] < 720
    table = np.array([114, 86, 67])
    assert all(np.linalg.norm(np.array(item["rgb"]) - table) > 60 for item in drawing.colors)
