"""Generador local guiado por referencia y trazos, optimizado para poca VRAM."""

from dataclasses import dataclass
import gc
from pathlib import Path
import re
from typing import Callable

import cv2
import numpy as np
from PIL import Image

from .config import Settings, STYLES
from .description import CharacterDescription
from .processing import color_name

INTERNAL_INSTRUCTION = (
    "Create a clean 2D front-facing cute virtual pet character based on this child's drawing. "
    "Preserve the main shape, dominant colors, and key features. Simplify messy details into "
    "a coherent design. The result should look like a charming cartoon mascot / sticker "
    "character with a white background."
)
NEGATIVE_PROMPT = (
    "photo, realistic, 3d render, human, scary, creepy, messy pencil sketch, paper texture, "
    "text, watermark, multiple characters, cropped body, side view, extra limbs, cluttered background"
)


@dataclass
class Generated:
    image: Image.Image
    device: str
    prompt: str
    negative_prompt: str
    warnings: list[str]


def build_prompt(description: CharacterDescription, style: str, palette: list[str],
                 preserve_colors: bool) -> str:
    creature = description.creature
    eyes = description.eyes
    ears = description.ears
    if eyes and "eye" not in eyes.lower():
        eyes += " eyes"
    if ears and "ear" not in ears.lower():
        ears += " ears"
    accessories = description.accessories
    if any(item in accessories.lower() for item in ("hat", "shirt", "scarf", "cape")):
        accessories = "wearing " + accessories
    features = ", ".join(filter(None, [eyes, ears,
                                      accessories, description.shape, description.expression]))
    colors = [color_name(c) for c in palette[:3]]
    color_text = (f"{colors[0]} main color" if colors else "pastel colors")
    if len(colors) > 1:
        color_text += ", " + " and ".join(dict.fromkeys(colors[1:])) + " accents"
    if not preserve_colors:
        # Descripciones pueden mencionar colores originales: al forzar paleta,
        # conservar rasgos, pero quitar palabras de color que compiten con ella.
        for color in ("red", "green", "blue", "yellow", "orange", "purple", "pink", "brown",
                      "black", "white", "gray", "grey", "teal", "turquoise", "violet"):
            creature = re.sub(rf"\b{color}\b", "", creature, flags=re.IGNORECASE)
            features = re.sub(rf"\b{color}\b", "", features, flags=re.IGNORECASE)
    creature = creature.strip() or "cartoon creature"
    # CLIP tiene 77 tokens: asegurar orientación, estilo, fondo e identidad
    # antes de detalles que podrían exceder su contexto.
    return f"front-facing full body, {STYLES[style]}, white background, {color_text}, one {creature}, {features}"


def white_exterior(image: Image.Image) -> Image.Image:
    """Normalizar solo blanco exterior conectado al borde; no borrar ojos."""
    rgb = np.array(image.convert("RGB"))
    near_white = ((rgb.min(axis=2) > 225) & (rgb.max(axis=2) - rgb.min(axis=2) < 20)).astype(np.uint8)
    count, labels = cv2.connectedComponents(near_white)
    if count > 1:
        border = np.unique(np.concatenate([labels[0], labels[-1], labels[:, 0], labels[:, -1]]))
        border = border[border != 0]
        rgb[np.isin(labels, border)] = 255
    return Image.fromarray(rgb)


class LocalGenerator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pipeline = None
        self.loaded_device = None

    def unload(self) -> None:
        if self.pipeline is None and self.loaded_device is None:
            return
        import torch
        self.pipeline = None
        self.loaded_device = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    def _load(self, paths: dict[str, Path], device: str) -> None:
        import torch
        from diffusers import ControlNetModel, DPMSolverMultistepScheduler, StableDiffusionControlNetImg2ImgPipeline
        if self.pipeline is not None and self.loaded_device == device:
            return
        self.unload()
        torch.set_num_threads(self.settings.cpu_threads)
        dtype = torch.float16 if device == "cuda" else torch.float32
        controlnet = ControlNetModel.from_pretrained(
            str(paths["control"]), torch_dtype=dtype, variant="fp16",
            use_safetensors=True, local_files_only=True,
        )
        pipeline = StableDiffusionControlNetImg2ImgPipeline.from_pretrained(
            str(paths["image"]), controlnet=controlnet, torch_dtype=dtype,
            variant="fp16", use_safetensors=True, local_files_only=True,
            safety_checker=None, feature_extractor=None, requires_safety_checker=False,
        )
        # DreamShaper trae DEIS: conservar el calendario de ruido, pero no
        # heredar sus opciones de solver al convertirlo a DPM++.
        pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
            pipeline.scheduler.config, algorithm_type="dpmsolver++",
            solver_type="midpoint", final_sigmas_type="zero",
        )
        pipeline.enable_vae_slicing()
        pipeline.enable_vae_tiling()
        if device == "cuda":
            # No llamar .to('cuda') antes de instalar offload.
            pipeline.enable_sequential_cpu_offload()
        else:
            pipeline.to("cpu")
        pipeline.set_progress_bar_config(disable=True)
        self.pipeline, self.loaded_device = pipeline, device

    def generate(self, paths: dict[str, Path], reference: Image.Image, control: Image.Image,
                 description: CharacterDescription, palette: list[str], style: str,
                 preserve_colors: bool, seed: int,
                 progress: Callable[[float, str], None], *,
                 prompt_override: str | None = None, negative_override: str | None = None) -> Generated:
        import torch
        prompt = prompt_override or build_prompt(description, style, palette, preserve_colors)
        negative = negative_override or NEGATIVE_PROMPT
        warnings = []
        device = "cuda" if torch.cuda.is_available() and self.settings.device != "cpu" else "cpu"
        if device == "cpu":
            warnings.append("Generación en CPU: puede tardar varios minutos.")
        for attempt in range(2):
            try:
                progress(0.48, f"Cargando generador local ({device.upper()})…")
                self._load(paths, device)
                # Limitar explícitamente al contexto de CLIP y guardar lo que
                # efectivamente leyó, en vez de perder rasgos silenciosamente.
                tokenizer = self.pipeline.tokenizer
                ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
                limit = tokenizer.model_max_length - 2
                effective_prompt = tokenizer.decode(ids[:limit])
                if len(ids) > limit:
                    warnings.append("Descripción abreviada para el contexto del generador.")
                def on_step(_pipeline, step, _timestep, callback_kwargs):
                    effective_steps = max(1, int(self.settings.steps * self.settings.strength))
                    progress(min(0.94, 0.55 + 0.39 * (step + 1) / effective_steps),
                             f"Dando vida al personaje · paso {step + 1}/{effective_steps} ({device.upper()})")
                    return callback_kwargs

                with torch.inference_mode():
                    result = self.pipeline(
                        prompt=effective_prompt, negative_prompt=negative,
                        image=reference, control_image=control,
                        height=self.settings.image_size, width=self.settings.image_size,
                        strength=self.settings.strength, num_inference_steps=self.settings.steps,
                        guidance_scale=self.settings.guidance,
                        controlnet_conditioning_scale=self.settings.control_scale,
                        generator=torch.Generator(device="cpu").manual_seed(seed),
                        callback_on_step_end=on_step,
                    )
                image = result.images[0].convert("RGB")
                if np.array(image).std() < 0.5:
                    raise FloatingPointError("El modelo produjo una imagen vacía; posible problema de precisión.")
                return Generated(white_exterior(image), device, effective_prompt, negative, warnings)
            except (RuntimeError, FloatingPointError) as exc:
                reason = str(exc).lower()
                recoverable = isinstance(exc, FloatingPointError) or any(
                    token in reason for token in ("out of memory", "cuda", "half", "nan", "inf")
                )
                if device != "cuda" or attempt or not recoverable:
                    raise
                self.unload()
                device = "cpu"
                warnings.append("CUDA no pudo completar la generación; reintentando en CPU float32 con la misma calidad.")
                progress(0.48, warnings[-1])
        raise RuntimeError("No se pudo generar el personaje.")
