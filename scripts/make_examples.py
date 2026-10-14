"""Generar dibujos de prueba con Pillow. No son resultados del modelo."""

from pathlib import Path
import sys

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def example(kind: str) -> Image.Image:
    image = Image.new("RGB", (700, 850), "#FAF8F0")
    draw = ImageDraw.Draw(image)
    dark = "#46413D"
    if kind == "conejo":
        draw.ellipse((220, 100, 300, 350), fill="#88C499", outline=dark, width=7)
        draw.ellipse((375, 105, 460, 350), fill="#88C499", outline=dark, width=7)
        draw.ellipse((210, 370, 480, 685), fill="#88C499", outline=dark, width=7)
        draw.ellipse((180, 265, 505, 525), fill="#88C499", outline=dark, width=7)
        draw.polygon([(240, 525), (455, 520), (465, 630), (232, 635)], fill="#DC6665", outline=dark, width=7)
        for box in [(225, 642, 330, 700), (365, 642, 475, 700)]:
            draw.ellipse(box, fill="#88C499", outline=dark, width=7)
    elif kind == "monstruo":
        draw.polygon([(185, 380), (160, 265), (260, 325)], fill="#A69DD6", outline=dark, width=7)
        draw.polygon([(440, 325), (540, 265), (515, 390)], fill="#A69DD6", outline=dark, width=7)
        draw.ellipse((180, 300, 525, 670), fill="#A69DD6", outline=dark, width=7)
        draw.ellipse((200, 610, 290, 700), fill="#A69DD6", outline=dark, width=7)
        draw.ellipse((415, 610, 510, 700), fill="#A69DD6", outline=dark, width=7)
        draw.polygon([(312, 240), (360, 130), (412, 242)], fill="#F4BC59", outline=dark, width=6)
        draw.ellipse((310, 222, 420, 265), fill="#F4BC59", outline=dark, width=6)
        draw.arc((290, 490, 420, 590), 0, 175, fill=dark, width=7)
    else:
        draw.polygon([(230, 330), (210, 185), (310, 310)], outline=dark, width=6)
        draw.polygon([(385, 310), (485, 185), (470, 345)], outline=dark, width=6)
        draw.ellipse((225, 410, 475, 680), outline=dark, width=6)
        draw.ellipse((180, 285, 520, 545), fill="#FAF8F0", outline=dark, width=6)
        draw.line([(470, 600), (540, 600), (570, 550), (545, 530)], fill=dark, width=7)
        for dx in [-14, 14]:
            draw.line([(210, 470 + dx), (130, 460 + dx)], fill=dark, width=4)
            draw.line([(490, 470 + dx), (570, 460 + dx)], fill=dark, width=4)
    for x in [270, 405]:
        draw.ellipse((x - 22, 375, x + 30, 435), fill="#FFFFFF", outline=dark, width=5)
        draw.ellipse((x - 4, 394, x + 12, 420), fill=dark)
    if kind != "monstruo":
        draw.polygon([(325, 452), (365, 452), (347, 470)], fill=dark)
        draw.arc((307, 454, 385, 498), 0, 180, fill=dark, width=5)
    # Suave desenfoque simula una foto y evita un fixture de píxeles perfectos.
    return image.filter(ImageFilter.GaussianBlur(0.45))


if __name__ == "__main__":
    destination = ROOT / "examples"
    destination.mkdir(exist_ok=True)
    for name in ["conejo", "monstruo", "gato_lapiz"]:
        example(name).save(destination / f"{name}.png")
    print(f"Dibujos de prueba guardados en {destination}")
