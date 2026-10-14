"""Interpretación visual automática en CPU, sin servicios externos."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import gc
import json
from pathlib import Path
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PIL import Image

from .config import Settings


@dataclass
class CharacterDescription:
    creature: str = "friendly cartoon creature"
    shape: str = "simple rounded silhouette"
    eyes: str = ""
    ears: str = ""
    accessories: str = ""
    expression: str = ""
    summary: str = ""
    species: str = "unknown"
    species_uncertain: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


INSTRUCTION = """Describe only the main character in this child's drawing.
Ignore the paper and surroundings. Do not add features you cannot see.
If species is unclear, say cartoon creature. Answer in English with ONLY a JSON
object containing these string keys: creature, shape, eyes, ears, accessories,
expression, summary. Use empty strings for unclear or absent features.
Also include species (dog, cat, duck, pig, rabbit, bear, other, or unknown)
and species_uncertain (a JSON boolean). Use unknown and true if ambiguous.
Keep each value short (under 10 words); summary under 25 words.
Include clothing (shirts), hats or carried objects in accessories if visible.
For eyes and ears, include the noun, e.g. "large eyes" or "long ears".
Describe visible colors in summary when present. No markdown."""


def parse_description(text: str) -> CharacterDescription:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("La descripción no contiene JSON.")
    data = json.loads(match.group())
    if not isinstance(data, dict) or not isinstance(data.get("creature"), str) or not data["creature"].strip():
        raise ValueError("La descripción no identifica una criatura.")
    fields = {}
    for key in ("creature", "shape", "eyes", "ears", "accessories", "expression", "summary"):
        value = data.get(key, "")
        if not isinstance(value, str):
            raise ValueError(f"El campo {key} no es texto.")
        # Longitudes acotadas; nunca pasar una respuesta completa como prompt.
        cleaned = " ".join(value.strip().split())
        if cleaned.lower() in {"none", "unknown", "unclear", "not visible", "n/a", "null"}:
            cleaned = ""
        fields[key] = cleaned[:180 if key == "summary" else 90]
    color_words = {"red", "green", "blue", "yellow", "orange", "purple", "pink", "brown",
                   "black", "white", "gray", "grey", "teal", "violet", "mint"}
    if not fields["creature"] or set(fields["creature"].lower().split()) <= color_words:
        fields["creature"] = "cartoon creature"
    if not fields["summary"]:
        fields["summary"] = ", ".join(filter(None, [fields["creature"], fields["shape"],
                                                    fields["eyes"], fields["ears"],
                                                    fields["accessories"], fields["expression"]]))[:180]
    species = data.get("species")
    uncertainty = data.get("species_uncertain")
    if species is not None and (not isinstance(species, str) or species not in {*SPECIES_ALIASES, "other", "unknown"}):
        raise ValueError("La especie no es válida.")
    if uncertainty is not None and not isinstance(uncertainty, bool):
        raise ValueError("La ambigüedad de especie debe ser un booleano.")
    # Compatibilidad con respuestas v1: buscar palabras completas, no subcadenas
    # ("bear" no debe coincidir con "bearded"). No usar accesorios para clasificar.
    inferred = identify_species(fields["creature"])
    fields["species"] = species or inferred
    fields["species_uncertain"] = uncertainty if uncertainty is not None else fields["species"] == "unknown"
    if fields["species"] == "unknown":
        fields["species_uncertain"] = True
    return CharacterDescription(**fields)


SPECIES_ALIASES = {
    "dog": ("dog", "puppy", "pup", "perro", "perrito"),
    "cat": ("cat", "kitten", "kitty", "gato", "gatito"),
    "duck": ("duck", "duckling", "pato", "patito"),
    "pig": ("pig", "piglet", "cerdo", "chanchito"),
    "rabbit": ("rabbit", "bunny", "conejo", "conejito"),
    "bear": ("bear", "teddy", "oso", "osito"),
}


def identify_species(creature: str) -> str:
    found = {species for species, aliases in SPECIES_ALIASES.items()
             if any(re.search(rf"\b{re.escape(alias)}\b", creature, re.I) for alias in aliases)}
    return next(iter(found)) if len(found) == 1 else "unknown"


def describe(image: Image.Image, model_path: Path, settings: Settings) -> tuple[CharacterDescription, list[str]]:
    from PIL import Image
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    torch.set_num_threads(settings.cpu_threads)
    processor = None
    model = None
    try:
        processor = AutoProcessor.from_pretrained(str(model_path), local_files_only=True)
        model = AutoModelForImageTextToText.from_pretrained(
            str(model_path), torch_dtype=torch.float32, attn_implementation="eager",
            low_cpu_mem_usage=True, local_files_only=True, use_safetensors=True,
        ).eval()
        # Una imagen estática; no cargar backend de vídeo ni Flash Attention.
        image = image.convert("RGB")
        image.thumbnail((768, 768), Image.Resampling.LANCZOS)
        for attempt in range(2):
            instruction = INSTRUCTION
            if attempt:
                instruction += '\nExample format: {"creature":"cartoon creature","shape":"round","eyes":"","ears":"","accessories":"","expression":"","summary":"A simple cartoon creature"}'
            messages = [{"role": "user", "content": [
                {"type": "image"}, {"type": "text", "text": instruction},
            ]}]
            text = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
            # El processor por defecto amplía a 1536 aunque el recorte ya sea
            # menor: limitar a 768 evita tiles redundantes sin perder detalle
            # de la imagen que le entregamos.
            inputs = processor(text=text, images=[image],
                               images_kwargs={"size": {"longest_edge": 768}}, return_tensors="pt")
            with torch.inference_mode():
                tokens = model.generate(**inputs, max_new_tokens=240, do_sample=False,
                                        repetition_penalty=1.08, use_cache=True)
            response = processor.batch_decode(tokens[:, inputs["input_ids"].shape[1]:],
                                               skip_special_tokens=True)[0]
            try:
                return parse_description(response), []
            except (ValueError, json.JSONDecodeError):
                continue
        return CharacterDescription(summary="A friendly creature based on the drawing"), [
            "La interpretación automática fue ambigua; se usó una descripción general y los trazos originales.",
        ]
    finally:
        # Descargar el modelo de visión antes de cargar el generador.
        del model, processor
        gc.collect()
