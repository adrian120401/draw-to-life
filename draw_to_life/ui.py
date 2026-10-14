"""Un taller visual sencillo. Sin fuentes remotas, enlaces públicos ni analytics."""

import html
import logging

import gradio as gr

from .config import ROOT, Settings
from .models import diagnose
from .pipeline import Pipeline
from .processing import load_image
from .preview import preview_html
from .rig import SPECIES, catalog_status

CSS = """
:root { --ink: #303c38; --paper: #fcf9f2; --mint: #34745d; }
body, .gradio-container { background: var(--paper) !important; }
.gradio-container { max-width: 1240px !important; margin: auto !important; }
#masthead { border-bottom: 1px solid #dfdfd3; padding: 22px 4px 24px; margin-bottom: 20px; }
#masthead .eyebrow { color: #557261; font: 700 11px 'Trebuchet MS',sans-serif;
    letter-spacing: 2px; text-transform: uppercase; }
#masthead h1 { font: 500 clamp(36px,5vw,56px)/1.05 Georgia,serif;
    color: var(--ink); margin: 12px 0 10px; letter-spacing: -1.6px; }
#masthead h1 span { color: var(--mint); font-style: italic; }
#masthead p { color: #52605a; font-size: 16px; max-width: 640px; line-height: 1.6; }
#process-button { background: #34745d; color: white; min-height: 50px; border: 0; }
#process-button:hover { background: #285d49; }
#final-panel { border: 2px solid #a8c9b3 !important; }
#journey { color: #627066; font-size: 13px; padding: 7px 0 15px; }
#footer { color: #66716a; font-size: 12px; margin-top: 22px; border-top: 1px solid #dfdfd3; padding-top: 14px; }
.palette-chip { display: inline-flex; align-items: center; gap: 7px; margin: 4px 12px 4px 0;
    font: 12px 'Trebuchet MS',sans-serif; color: #36423b; }
.palette-chip i { display: inline-block; width: 19px; height: 19px; border-radius: 50%; border: 1px solid #aaa; }
@media(prefers-reduced-motion:reduce) { * { animation: none !important; transition: none !important; } }
"""


def palette_html(colors: list[str]) -> str:
    # Colores provienen de valid_hex/detección; escapar texto igualmente.
    return "".join(f'<span class="palette-chip"><i style="background:{html.escape(color)}"></i>{html.escape(color)}</span>'
                   for color in colors)


def error_html(message: str) -> str:
    return ('<div role="alert" style="padding:32px;text-align:center">'
            '<h3>No se pudo dar vida al dibujo</h3>'
            f'<p>{html.escape(message)}</p>'
            '<p>Revisá el mensaje y volvé a intentarlo.</p></div>')


def build_ui(settings: Settings) -> gr.Blocks:
    report = diagnose(settings)
    pipeline = Pipeline(settings)
    cuda_ok = settings.device != "cuda" or report["cuda_available"]
    catalog = catalog_status(settings.catalog_dir)
    ready = report["character_ready"] and cuda_ok
    if ready:
        gpu = report["gpu"]["name"] if report["gpu"] and settings.device != "cpu" else "CPU · generación lenta"
        environment = f"**Modelos listos · {gpu}**. Todo el procesamiento se hace en esta PC.\n\n" \
                      f"**Bases preparadas: {len(catalog['ready'])}/6**. " \
                      "Para completar el catálogo: `./scripts/prepare-characters.ps1`."
    else:
        reason = report["character_error"] or "CUDA no está disponible para DEVICE=cuda."
        environment = f"**Preparación pendiente.** {reason}\n\nEn PowerShell: `./scripts/download-models.ps1` y luego reiniciá la app."
    theme = gr.themes.Base(primary_hue="green", neutral_hue="stone",
                           font=["Trebuchet MS", "sans-serif"], font_mono=["Consolas", "monospace"])
    with gr.Blocks(title="Draw to Life · Mascotas animadas", theme=theme, css=CSS, analytics_enabled=False) as demo:
        gr.HTML('<header id="masthead"><div class="eyebrow">Un pequeño taller de imaginación · mascotas animadas</div>'
                '<h1>Draw to <span>Life.</span></h1>'
                '<p>Ese personaje que vive en una hoja, ahora tiene un lugar en la pantalla. '
                'Subí su dibujo y convertí su idea en una mascota que respira, parpadea y te saluda.</p></header>')
        gr.Markdown(environment)
        gr.HTML('<div id="journey">01 · Tu dibujo &nbsp; → &nbsp; 02 · Lo entendemos &nbsp; → &nbsp; 03 · Le damos vida</div>')
        with gr.Row():
            with gr.Column(scale=5):
                source = gr.File(label="Subí una foto del dibujo", file_types=[".jpg", ".jpeg", ".png", ".webp"], type="filepath")
                original = gr.Image(label="01 · Imagen original", interactive=False, height=300, show_download_button=False)
                with gr.Row():
                    style = gr.State("Cartoon infantil")
                    color_mode = gr.Radio(["Colores del dibujo", "Paleta por defecto"], value="Colores del dibujo", label="Colores")
                with gr.Accordion("Cómo crear tu mascota", open=False):
                    mode = gr.Dropdown([("Elegir automáticamente", "auto"), ("Adaptar una base", "template"),
                                        ("Crear desde cero", "free")], value="auto", label="Creación")
                    animal = gr.Dropdown([("Reconocer el dibujo", "auto"), *[(label, key) for key, label in SPECIES.items()]],
                                         value="auto", label="Animal")
                    gr.Markdown("Podés corregir el animal detectado. Si no hay una base adecuada, el modo automático crea una mascota nueva.")
                with gr.Accordion("Tu paleta por defecto", open=False):
                    gr.Markdown("Se usa en dibujos sin color o cuando elegís «Paleta por defecto».")
                    with gr.Row():
                        primary = gr.ColorPicker(value=settings.palette[0], label="Principal")
                        secondary = gr.ColorPicker(value=settings.palette[1], label="Secundario")
                        accent = gr.ColorPicker(value=settings.palette[2], label="Acento")
                button = gr.Button("Dar vida al dibujo", variant="primary", interactive=ready, elem_id="process-button")
                gr.Markdown("Un personaje por foto. Papel claro, buena luz y el dibujo completo funcionan mejor.")
            with gr.Column(scale=6):
                animated = gr.HTML('<p style="text-align:center;padding:120px 0">Tu mascota aparecerá acá.</p>', elem_id="final-panel")
                status = gr.Markdown("Esperando tu primer dibujo.")
                bundle = gr.File(label="Descargar personaje animado · ZIP", interactive=False)
                with gr.Accordion("Imagen de portada", open=False):
                    final = gr.Image(label="Vista estática", interactive=False, height=280, format="png")
                    download = gr.File(label="Descargar portada PNG", interactive=False)
                with gr.Accordion("Así entendimos tu dibujo", open=False):
                    description = gr.JSON(label="Descripción automática")
                    colors = gr.HTML()
                    metadata = gr.File(label="Metadata de la ejecución", interactive=False)
        with gr.Accordion("02 · Del papel al personaje", open=False):
            with gr.Row():
                cropped = gr.Image(label="Recorte y limpieza", interactive=False, height=280)
                isolated = gr.Image(label="Dibujo aislado · fondo transparente", interactive=False, height=280, image_mode="RGBA", format="png")
        examples = sorted((ROOT / "examples").glob("*.png"))
        if (ROOT / "test1.png").is_file():
            examples.insert(0, ROOT / "test1.png")
        if examples:
            gr.Examples(examples=[[str(path)] for path in examples], inputs=[source], label="Probá con un dibujo de muestra", cache_examples=False)
        gr.HTML('<div id="footer">100% local después de descargar los modelos · Sin API keys · '
                'Una interpretación nueva de tu dibujo, hecha con su misma imaginación.</div>')

        def preview(file):
            if not file:
                return None, None, None, None, None, None, None, "", "Esperando tu primer dibujo.", "", None
            try:
                image = load_image(file)
            except ValueError as exc:
                raise gr.Error(str(exc)) from exc
            return image, None, None, None, None, None, None, "", "Dibujo cargado. Dale vida a tu mascota.", "", None

        outputs = [cropped, isolated, final, download, metadata, description, colors, status, animated, bundle]

        def process(file, selected_style, selected_colors, p, s, a, selected_mode, selected_animal, progress=gr.Progress()):
            if not file:
                raise gr.Error("Primero cargá una foto del dibujo.")
            # Limpiar el personaje anterior antes de mostrar otro trabajo.
            yield None, None, None, None, None, None, "", "Preparando tu dibujo…", "", None
            run = None
            try:
                progress(0.03, desc="Separando el dibujo del papel…")
                run = pipeline.prepare(file, selected_style, selected_colors, [p, s, a], mode=selected_mode, animal=selected_animal)
                yield (run.drawing.cropped, run.drawing.isolated, None, None,
                       str(run.directory / "metadata.json"), None, palette_html(run.palette),
                       "Recorte listo. Estamos entendiendo el dibujo y preparando su mascota…", "", None)
                result = pipeline.finish(run, lambda fraction, message: progress(fraction, desc=message))
                warnings = "\n\n" + "\n\n".join(run.metadata["warnings"]) if run.metadata["warnings"] else ""
                yield (run.drawing.cropped, run.drawing.isolated, str(result), str(result),
                       str(run.directory / "metadata.json"), run.metadata["description"], palette_html(run.palette),
                       f"**Tu mascota está lista.** "
                       f"{'Base adaptada' if run.metadata.get('generation_mode') == 'template' else 'Personaje nuevo'} · "
                       f"{run.metadata['duration_seconds']:.0f} s.{warnings}",
                       preview_html(run.puppet), str(run.directory / "character.zip"))
            except Exception as exc:
                logging.getLogger(__name__).exception("No se pudo procesar la imagen")
                if run:
                    yield (run.drawing.cropped, run.drawing.isolated, None, None,
                           str(run.directory / "metadata.json"), run.metadata.get("description"),
                           palette_html(run.palette), f"**No se pudo generar el personaje.** {exc}", error_html(str(exc)), None)
                else:
                    yield None, None, None, None, None, None, "", f"**No se pudo procesar la foto.** {exc}", error_html(str(exc)), None

        source.change(preview, [source], [original] + outputs, concurrency_id="drawing", concurrency_limit=1)
        button.click(process, [source, style, color_mode, primary, secondary, accent, mode, animal], outputs,
                     concurrency_id="drawing", concurrency_limit=1)
    demo.queue(default_concurrency_limit=1, max_size=3, api_open=False)
    return demo
