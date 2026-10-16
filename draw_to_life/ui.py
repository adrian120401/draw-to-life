"""Subir, crear y jugar. El diagnóstico técnico queda en los logs."""

import html
import logging
from queue import SimpleQueue
from threading import Thread

import gradio as gr

from .config import Settings
from .models import diagnose
from .pipeline import Pipeline
from .preview import preview_html
from .processing import load_image
from .scene import DECORATIONS, SCENE_CSS, icon

LOGGER = logging.getLogger(__name__)

CSS = SCENE_CSS + """
body, .gradio-container { background: var(--lilac) !important; }
.gradio-container { max-width: none !important; padding: 0 !important; }
.gradio-container footer { display: none !important; }
.gradio-container > main { padding: 0 !important; max-width: none !important; width: 100% !important; margin: 0 !important; }
.gradio-container .html-container { padding: 0 !important; }
#scenery { position: absolute; height: 0; min-height: 0; padding: 0; border: 0; }
#upload-step, #loading-step { position: relative; min-height: 100svh; justify-content: center;
    align-items: center; gap: 24px; padding: 28px 20px; background: transparent; }
#upload-picture { width: 148px; padding: 0; border: 0; overflow: visible !important; background: transparent; }
.photo-token { display: grid; place-items: center; width: 148px; height: 170px;
    background: var(--cream); border-radius: 24px; transform: rotate(-8deg);
    box-shadow: 0 12px 30px #63458113; }
.photo-token svg { width: 78px; height: 78px; color: #ad89cd; stroke-width: 1.2; }
#upload-picture svg { color: #ad89cd; }
#upload-button, #retry-button { width: auto !important; min-width: 224px; flex: none;
    background: var(--violet); color: white; border: 0; border-radius: 22px;
    padding: 19px 30px; font: 700 20px 'Trebuchet MS',sans-serif; box-shadow: 0 6px 18px #69418d20; }
#upload-button:hover, #retry-button:hover { background: #5d3688; }
#upload-button:disabled { opacity: .55; }
#retry-button { min-width: 180px; padding: 14px 24px; font-size: 17px; }
#upload-error { max-width: 360px; border: 0; background: transparent; padding: 0; }
.upload-error { text-align: center; color: var(--ink); font-size: 16px; line-height: 1.5; }
#loading-art { border: 0; background: transparent; width: 260px; padding: 0; }
.creating { text-align: center; color: var(--ink); }
.creating p { margin: 26px 0 0; font: 700 20px 'Trebuchet MS',sans-serif; }
.creating-orbit { width: 112px; height: 112px; margin: auto; border-radius: 40% 60% 55% 45%;
    background: #ccb1ec; display: grid; place-items: center; animation: imagining 3s ease-in-out infinite; }
.creating-orbit svg { width: 54px; height: 54px; color: #fffaf1; }
@keyframes imagining { 0%,100% { transform: rotate(-10deg) scale(.94); border-radius: 40% 60% 55% 45%; }
    50% { transform: rotate(12deg) scale(1.04); border-radius: 60% 40% 45% 55%; } }
#result-step { position: relative; gap: 0; min-height: 100svh; background: transparent; }
#final-panel { padding: 0; border: 0; background: transparent; }
#result-actions { width: min(100%, 420px); align-self: center; justify-content: center; padding: 0 16px 20px; gap: 16px; }
#result-actions button, #result-actions a { background: transparent; color: var(--ink); border: 0;
    box-shadow: none; font: 400 14px 'Trebuchet MS',sans-serif; min-width: 120px; min-height: 44px; padding: 12px 8px; }
#result-actions button:hover, #result-actions a:hover { background: #dbcbed; }
#setup-notice { max-width: 360px; text-align: center; color: var(--ink); }
@media(max-width:480px) {
    #upload-step, #loading-step { gap: 28px; }
    #result-actions { padding-bottom: 12px; }
}
"""


def error_html(message: str) -> str:
    return f'<div class="upload-error" role="alert">{html.escape(message)}</div>'


def loading_html(message: str) -> str:
    return ('<div class="creating" role="status" aria-live="polite">'
            f'<div class="creating-orbit" aria-hidden="true">{icon("heart")}</div>'
            f'<p>{html.escape(message)}</p></div>')


def generation_events(pipeline, run):
    """Publicar cambios de etapa mientras el pipeline síncrono trabaja.

    Una única thread conserva el orden visión/difusión. Siempre se espera su
    cierre antes de liberar la cola, incluso si se desconecta el navegador.
    """
    events = SimpleQueue()

    def finish():
        last = None

        def progress(fraction, _message):
            nonlocal last
            label = "Mirando tu dibujo…" if fraction < .35 else "Dándole vida…"
            if label != last:
                events.put(("phase", label))
                last = label

        try:
            pipeline.finish(run, progress)
            events.put(("done", None))
        except Exception as exc:
            events.put(("error", exc))

    worker = Thread(target=finish, name="draw-to-life-generation", daemon=True)
    worker.start()
    try:
        while True:
            event, value = events.get()
            if event == "error":
                raise value
            if event == "done":
                break
            yield value
    finally:
        worker.join()


def build_ui(settings: Settings) -> gr.Blocks:
    report = diagnose(settings)
    pipeline = Pipeline(settings)
    ready = report["character_ready"] and (settings.device != "cuda" or report["cuda_available"])
    if not ready:
        LOGGER.warning("Preparación pendiente: %s", report.get("character_error") or "CUDA no disponible")
    theme = gr.themes.Base(primary_hue="purple", neutral_hue="purple",
                           font=["Trebuchet MS", "sans-serif"], font_mono=["Consolas", "monospace"])
    with gr.Blocks(title="Draw to Life", theme=theme, css=CSS, analytics_enabled=False) as demo:
        gr.HTML(DECORATIONS, elem_id="scenery")
        phase = gr.State("upload")
        with gr.Column(elem_id="upload-step") as upload_step:
            gr.HTML(f'<div class="photo-token" aria-hidden="true">{icon("photo")}</div>', elem_id="upload-picture")
            source = gr.UploadButton("Subí tu dibujo", file_types=[".jpg", ".jpeg", ".png", ".webp"],
                                     type="filepath", interactive=ready, elem_id="upload-button")
            error = gr.HTML("", elem_id="upload-error")
            retry = gr.Button("Reintentar", visible=False, elem_id="retry-button")
            if not ready:
                gr.Markdown("La app necesita prepararse antes de crear tu mascota.", elem_id="setup-notice")
                with gr.Accordion("Preparar la app", open=False):
                    gr.Markdown("Ejecutá `scripts/download-models.ps1` y reiniciá la app. "
                                "Si configuraste CUDA, comprobá que esté disponible.")
        with gr.Column(visible=False, elem_id="loading-step") as loading_step:
            loading = gr.HTML(loading_html("Mirando tu dibujo…"), elem_id="loading-art")
        with gr.Column(visible=False, elem_id="result-step") as result_step:
            animated = gr.HTML("", elem_id="final-panel")
            with gr.Row(elem_id="result-actions"):
                again = gr.Button("Otro dibujo", variant="secondary")
                download = gr.DownloadButton("Guardar mascota", visible=False, variant="secondary")

        outputs = [upload_step, loading_step, result_step, loading, animated, download, error, retry, phase]

        def screen(step, message="Mirando tu dibujo…", player="", package=None, problem="", can_retry=False):
            return (gr.update(visible=step == "upload"), gr.update(visible=step == "processing"),
                    gr.update(visible=step == "result"), loading_html(message), player,
                    gr.update(value=package, visible=package is not None),
                    error_html(problem) if problem else "", gr.update(visible=can_retry), step)

        def begin():
            return screen("processing")

        def process(file):
            yield screen("processing")
            if not ready:
                yield screen("upload", problem="Prepará la app y volvé a intentarlo.")
                return
            try:
                if not file:
                    raise ValueError("Primero subí una foto de tu dibujo.")
                load_image(file)
            except (ValueError, OSError) as exc:
                yield screen("upload", problem=str(exc))
                return
            try:
                run = pipeline.prepare(file, "Cartoon infantil", "Colores del dibujo", list(settings.palette),
                                       mode="auto", animal="auto")
                for message in generation_events(pipeline, run):
                    yield screen("processing", message=message)
                player = preview_html(run.puppet)
                yield screen("result", player=player, package=str(run.directory / "character.zip"))
            except Exception:
                LOGGER.exception("No se pudo dar vida al dibujo")
                yield screen("upload", problem="No pudimos darle vida. Probá otra vez o subí otro dibujo.", can_retry=True)

        def reset():
            return (*screen("upload"), None)

        for trigger in (source.upload, retry.click):
            trigger(begin, outputs=outputs, queue=False, show_progress="hidden").then(
                process, [source], outputs, concurrency_id="drawing", concurrency_limit=1,
                show_progress="hidden", trigger_mode="once")
        again.click(reset, outputs=[*outputs, source], queue=False, show_progress="hidden")
    demo.queue(default_concurrency_limit=1, max_size=3, api_open=False)
    return demo
