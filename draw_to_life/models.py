"""Descarga explícita y diagnóstico. La generación solo abre snapshots locales."""

import argparse
import json
from pathlib import Path

from .config import Settings


class ModelError(RuntimeError):
    pass


def model_specs(settings: Settings, include_character: bool = False) -> dict:
    specs = {
        "vision": (settings.vision_model, ["*.json", "*.jinja", "*.txt", "*.model", "*.safetensors"]),
        "image": (settings.image_model, [
            "model_index.json", "scheduler/*", "tokenizer/*",
            "unet/config.json", "unet/*.fp16.safetensors",
            "vae/config.json", "vae/*.fp16.safetensors",
            "text_encoder/config.json", "text_encoder/*.fp16.safetensors",
        ]),
        "control": (settings.control_model, ["config.json", "diffusion_pytorch_model.fp16.safetensors"]),
    }
    if include_character:
        specs["character"] = (settings.character_model, specs["image"][1])
    return specs


def validate_snapshot(kind: str, path: Path) -> None:
    """Un snapshot parcial no debe marcarse como listo solo por tener carpeta."""
    if kind in {"image", "character"}:
        required = ["model_index.json", "scheduler/scheduler_config.json", "tokenizer/vocab.json",
                    "tokenizer/merges.txt", "tokenizer/tokenizer_config.json"]
        for component, filename in (
            ("unet", "diffusion_pytorch_model.fp16.safetensors"),
            ("vae", "diffusion_pytorch_model.fp16.safetensors"),
            ("text_encoder", "model.fp16.safetensors"),
        ):
            required.extend([f"{component}/config.json", f"{component}/{filename}"])
    elif kind == "control":
        required = ["config.json", "diffusion_pytorch_model.fp16.safetensors"]
    elif kind == "vision":
        required = ["config.json", "preprocessor_config.json", "tokenizer_config.json"]
        index = path / "model.safetensors.index.json"
        if index.is_file():
            try:
                required.extend(set(json.loads(index.read_text(encoding="utf-8"))["weight_map"].values()))
            except (KeyError, ValueError) as exc:
                raise ModelError("Índice de pesos de visión inválido; volvé a descargar los modelos.") from exc
        else:
            required.append("model.safetensors")
        if not any((path / name).is_file() for name in ("tokenizer.json", "tokenizer.model")):
            required.append("tokenizer.json")
    else:
        raise ValueError(f"Tipo de modelo desconocido: {kind}")
    missing = [name for name in required if not (path / name).is_file() or (path / name).stat().st_size == 0]
    if missing:
        raise ModelError(f"Modelo {kind} incompleto: {', '.join(missing[:4])}. Ejecutá download-models.")
    # Comprobar el formato sin cargar tensores: detecta pesos truncados antes
    # de habilitar la UI, aun si sus nombres y tamaños no nulos parecen válidos.
    from safetensors import safe_open
    for filename in required:
        if filename.endswith(".safetensors"):
            try:
                with safe_open(str(path / filename), framework="np"):
                    pass
            except Exception as exc:
                raise ModelError(f"Pesos incompletos o dañados en {kind}/{filename}. Volvé a descargar los modelos.") from exc


def local_models(settings: Settings, include_character: bool = False) -> dict[str, Path]:
    from huggingface_hub import snapshot_download
    paths = {}
    for kind, (repo, patterns) in model_specs(settings, include_character).items():
        try:
            path = Path(snapshot_download(repo, cache_dir=settings.cache_dir,
                                          allow_patterns=patterns, local_files_only=True))
        except Exception as exc:
            raise ModelError(f"Falta el modelo {repo}. Ejecutá primero download-models (requiere internet).") from exc
        validate_snapshot(kind, path)
        paths[kind] = path
    return paths


def download_models(settings: Settings, include_character: bool = True) -> dict[str, Path]:
    from huggingface_hub import snapshot_download
    paths = {}
    for kind, (repo, patterns) in model_specs(settings, include_character).items():
        print(f"\nDescargando {kind}: {repo}", flush=True)
        path = Path(snapshot_download(repo, cache_dir=settings.cache_dir,
                                      allow_patterns=patterns, max_workers=2))
        validate_snapshot(kind, path)
        paths[kind] = path
    return paths


def diagnose(settings: Settings) -> dict:
    import torch
    torch.set_num_threads(settings.cpu_threads)
    cuda = torch.cuda.is_available()
    gpu = None
    cuda_error = None
    if cuda:
        try:
            # is_available() solo detecta driver; este kernel verifica la build.
            probe = torch.ones(1, device="cuda") + 1
            torch.cuda.synchronize()
            del probe
            properties = torch.cuda.get_device_properties(0)
            gpu = {"name": properties.name, "vram_gb": round(properties.total_memory / 1024**3, 2)}
        except Exception as exc:
            cuda = False
            cuda_error = str(exc)
    report = {"torch": torch.__version__, "cuda_available": cuda, "gpu": gpu,
              "requested_device": settings.device, "cuda_error": cuda_error,
              "models_ready": False, "models": {}, "model_error": None}
    try:
        paths = local_models(settings)
        report["models_ready"] = True
        report["models"] = {key: str(value) for key, value in paths.items()}
    except ModelError as exc:
        report["model_error"] = str(exc)
    report["character_ready"] = False
    report["character_error"] = None
    try:
        from dataclasses import replace
        character_paths = local_models(replace(settings, image_model=settings.character_model))
        report["character_ready"] = True
        report["character_models"] = {key: str(value) for key, value in character_paths.items()}
    except ModelError as exc:
        report["character_error"] = str(exc)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Preparación de modelos locales de Draw to Life")
    parser.add_argument("command", choices=["download-models", "doctor"])
    args = parser.parse_args()
    settings = Settings.from_env()
    try:
        if args.command == "download-models":
            paths = download_models(settings)
            print(json.dumps({k: str(v) for k, v in paths.items()}, indent=2))
            return 0
        report = diagnose(settings)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if (report["models_ready"] and report["character_ready"] and
                     (settings.device != "cuda" or report["cuda_available"])) else 1
    except Exception as exc:
        print(f"No se pudo preparar el entorno: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
