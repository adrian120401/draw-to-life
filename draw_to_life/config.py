"""Configuración compartida. No importa torch ni carga modelos al abrir la UI."""

from dataclasses import dataclass
import os
from pathlib import Path
import re

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Deben establecerse antes de importar Gradio / Hugging Face.
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

STYLES = {
    "Cartoon infantil": "adorable children's game mascot, 2D cartoon, big head, vibrant colors, soft cel shading",
    "Sticker": "cute 2D cartoon sticker, bold smooth outline, flat colors",
    "Cartoon suave": "cute 2D cartoon, soft pastel shading, smooth rounded shapes",
    "Mascota virtual": "cute 2D virtual pet mascot, simple rounded body, expressive face",
}


def valid_hex(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", value):
        raise ValueError("Cada color debe tener formato hexadecimal, por ejemplo #91CDB5.")
    return value.upper()


@dataclass(frozen=True)
class Settings:
    output_dir: Path
    cache_dir: Path | None
    vision_model: str
    image_model: str
    control_model: str
    device: str
    image_size: int
    steps: int
    strength: float
    control_scale: float
    guidance: float
    cpu_threads: int
    palette: tuple[str, str, str]
    port: int
    character_model: str = "Lykon/dreamshaper-8"
    catalog_dir: Path = ROOT / "assets" / "characters"
    adaptation_strength: float = 0.30
    catalog_strength: float = 0.55
    catalog_steps: int = 40
    part_image_size: int = 384

    @classmethod
    def from_env(cls) -> "Settings":
        output = Path(os.getenv("OUTPUT_DIR", "outputs")).expanduser()
        cache = os.getenv("MODEL_CACHE_DIR", "").strip()
        cache_path = Path(cache).expanduser() if cache else None
        if cache_path and not cache_path.is_absolute():
            cache_path = ROOT / cache_path
        settings = cls(
            output_dir=output if output.is_absolute() else ROOT / output,
            cache_dir=cache_path,
            vision_model=os.getenv("VISION_MODEL_ID", "HuggingFaceTB/SmolVLM2-2.2B-Instruct"),
            image_model=os.getenv("IMAGE_MODEL_ID", "stable-diffusion-v1-5/stable-diffusion-v1-5"),
            control_model=os.getenv("CONTROL_MODEL_ID", "lllyasviel/control_v11p_sd15_scribble"),
            device=os.getenv("DEVICE", "auto").lower(),
            image_size=int(os.getenv("IMAGE_SIZE", "512")),
            steps=int(os.getenv("INFERENCE_STEPS", "30")),
            strength=float(os.getenv("IMAGE_STRENGTH", "0.65")),
            control_scale=float(os.getenv("CONTROL_SCALE", "0.7")),
            guidance=float(os.getenv("GUIDANCE_SCALE", "7.0")),
            cpu_threads=int(os.getenv("CPU_THREADS", "4")),
            palette=tuple(valid_hex(os.getenv(key, default)) for key, default in (
                ("PALETTE_PRIMARY", "#91CDB5"),
                ("PALETTE_SECONDARY", "#FFE2A8"),
                ("PALETTE_ACCENT", "#F39AA8"),
            )),
            port=int(os.getenv("PORT", "7860")),
            character_model=os.getenv("CHARACTER_MODEL_ID", "Lykon/dreamshaper-8"),
            catalog_dir=Path(os.getenv("CHARACTER_CATALOG_DIR", str(ROOT / "assets" / "characters"))).expanduser(),
            adaptation_strength=float(os.getenv("ADAPTATION_STRENGTH", "0.30")),
            catalog_strength=float(os.getenv("CATALOG_STRENGTH", "0.55")),
            catalog_steps=int(os.getenv("CATALOG_STEPS", "40")),
            part_image_size=int(os.getenv("PART_IMAGE_SIZE", "384")),
        )
        if settings.device not in {"auto", "cuda", "cpu"}:
            raise ValueError("DEVICE debe ser auto, cuda o cpu.")
        if settings.image_size % 8 or not 256 <= settings.image_size <= 768:
            raise ValueError("IMAGE_SIZE debe ser múltiplo de 8, entre 256 y 768.")
        if not 5 <= settings.steps <= 80 or not 0.1 <= settings.strength <= 0.95:
            raise ValueError("Revisá INFERENCE_STEPS (5–80) e IMAGE_STRENGTH (0.1–0.95).")
        if not 0 <= settings.control_scale <= 2 or not 1 <= settings.guidance <= 20:
            raise ValueError("Revisá CONTROL_SCALE (0–2) y GUIDANCE_SCALE (1–20).")
        if settings.cpu_threads < 1 or not 1024 <= settings.port <= 65535:
            raise ValueError("CPU_THREADS debe ser positivo y PORT debe estar entre 1024 y 65535.")
        if not settings.catalog_dir.is_absolute():
            settings = cls(**{**settings.__dict__, "catalog_dir": ROOT / settings.catalog_dir})
        if not 0.1 <= settings.adaptation_strength <= 0.6 or not 0.1 <= settings.catalog_strength <= 0.95:
            raise ValueError("Revisá ADAPTATION_STRENGTH (0.1–0.6) y CATALOG_STRENGTH (0.1–0.95).")
        if not 5 <= settings.catalog_steps <= 80:
            raise ValueError("CATALOG_STEPS debe estar entre 5 y 80.")
        if settings.part_image_size % 8 or not 256 <= settings.part_image_size <= 768:
            raise ValueError("PART_IMAGE_SIZE debe ser múltiplo de 8 entre 256 y 768.")
        return settings
