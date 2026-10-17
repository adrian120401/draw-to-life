from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
import pytest

from draw_to_life.processing import DrawingError, load_image, make_references, preprocess
from scripts.make_examples import example


def test_colored_rabbit_preserves_ears_and_red_shirt():
    drawing = preprocess(example("conejo"))
    assert drawing.has_color
    assert drawing.bbox[1] < 110
    assert drawing.bbox[3] >= 700
    colors = [item["rgb"] for item in drawing.colors]
    assert any(g > r * 1.15 and g > b for r, g, b in colors)
    assert any(r > g * 1.3 and r > b * 1.3 for r, g, b in colors)
    rgba = np.array(drawing.isolated)
    assert rgba[0, 0, 3] == 0
    # Ojos blancos y áreas encerradas deben seguir opacos.
    assert np.count_nonzero((rgba[:, :, :3].min(axis=2) > 245) & (rgba[:, :, 3] == 255)) > 300


def test_paper_normalization_preserves_dominant_color_values():
    drawing = preprocess(example("conejo"))
    colors = np.array([item["rgb"] for item in drawing.colors])
    for expected in ([136, 196, 153], [220, 102, 101]):
        assert np.min(np.linalg.norm(colors - expected, axis=1)) < 30


def test_pencil_uses_palette_and_has_a_nonempty_control():
    drawing = preprocess(example("gato_lapiz"))
    assert not drawing.has_color
    reference, control = make_references(drawing, 512, ["#91CDB5", "#FFE2A8", "#F39AA8"], False)
    rgb = np.array(reference)
    assert reference.size == control.size == (512, 512)
    assert np.count_nonzero(np.all(rgb == [145, 205, 181], axis=2)) > 500
    assert np.count_nonzero(np.array(control)) > 300
    assert np.array(control)[0, 0].max() == 0


def test_forced_palette_removes_original_colors():
    drawing = preprocess(example("conejo"))
    reference, _ = make_references(drawing, 512, ["#7A91DF", "#FFE2A8", "#F39AA8"], False)
    rgb = np.array(reference)
    assert not np.any((rgb[:, :, 0] > 175) & (rgb[:, :, 1] < 130) & (rgb[:, :, 2] < 130))
    assert np.count_nonzero(np.all(rgb == [122, 145, 223], axis=2)) > 500


def test_blank_paper_is_rejected():
    with pytest.raises(DrawingError, match="trazos"):
        preprocess(Image.new("RGB", (800, 900), "white"))


def test_table_is_not_selected_as_character():
    paper = example("conejo").resize((490, 595))
    photo = Image.new("RGB", (700, 850), "#725643")
    photo.paste(paper, (100, 100))
    drawing = preprocess(photo)
    assert drawing.bbox[0] > 150
    assert drawing.bbox[2] < 550
    assert drawing.has_color


def test_small_detached_feature_is_retained():
    image = Image.new("RGB", (600, 600), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((160, 160, 440, 500), outline="#444444", width=7)
    draw.ellipse((245, 125, 265, 145), fill="#444444")
    drawing = preprocess(image)
    assert drawing.bbox[1] < 125


def test_original_coordinates_after_resize():
    large = example("conejo").resize((1400, 1700))
    drawing = preprocess(large)
    assert drawing.source_size == (1400, 1700)
    assert drawing.bbox[1] < 220
    assert drawing.bbox[3] > 1400


def test_invalid_file_and_transparent_input(tmp_path: Path):
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"this is not a picture")
    with pytest.raises(DrawingError, match="leer"):
        load_image(broken)
    transparent = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    path = tmp_path / "transparent.png"
    transparent.save(path)
    assert np.array(load_image(path))[0, 0].tolist() == [255, 255, 255]


@pytest.mark.parametrize("extension", [".heic", ".heif"])
def test_phone_heic_is_read_with_correct_orientation(tmp_path, extension):
    image = Image.new("RGB", (80,40), "#80c090")
    exif = Image.Exif()
    exif[274] = 6
    path = tmp_path / ("camera" + extension)
    image.save(path, format="HEIF", exif=exif.tobytes())
    loaded = load_image(path)
    assert loaded.mode == "RGB"
    assert loaded.size == (40,80)


def test_corrupt_phone_capture_is_rejected(tmp_path):
    path = tmp_path / "broken.heic"
    path.write_bytes(b"not a camera photo")
    with pytest.raises(DrawingError, match="leer"):
        load_image(path)
