"""Preview autosuficiente en iframe: funciona con Gradio 5, sin CDN ni fetch."""

import base64
import html
from io import BytesIO
import json

from .rig import Puppet, RUNTIME
from .scene import DECORATIONS, SCENE_CSS, icon


def preview_document(puppet: Puppet, *, embedded: bool = False) -> str:
    assets = {}
    for name, texture in puppet.textures.items():
        buffer = BytesIO()
        texture.save(buffer, format="PNG")
        assets[name] = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    payload = json.dumps({"manifest": puppet.manifest, "assets": assets}, ensure_ascii=True).replace("<", "\\u003c")
    runtime = RUNTIME.read_text(encoding="utf-8")
    scene_style = SCENE_CSS
    if embedded:
        # El fondo pertenece a la pantalla completa, no a la caja del iframe.
        scene_style += "html,body{background:transparent}.playroom-shapes{display:none}"
    controls = "".join(
        f'<button class="pet-action" data-action="{action}" disabled aria-pressed="false">'
        f'<span class="action-icon">{icon(symbol)}</span><span>{label}</span></button>'
        for action, symbol, label in (("feed", "food", "Comida"), ("pet", "heart", "Mimos"), ("play", "play", "Jugar")))
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,">'
            '<title>Tu mascota</title><style>' + scene_style + '</style></head><body>'
            + DECORATIONS + '<main class="pet-room"><div class="pet-stage">'
            '<canvas id="pet" role="button" tabindex="0" aria-label="Darle mimos a tu mascota"></canvas>'
            '<button class="pet-utility" id="pause" aria-label="Pausar" aria-pressed="false" disabled>'
            + icon("pause") + '</button></div><div class="pet-controls" role="group" aria-label="Jugar con tu mascota">'
            + controls + '</div><p id="activity" class="sr-only" role="status" aria-live="polite"></p>'
            '<p id="error" class="pet-error" role="alert" hidden></p></main><script>'
            + runtime + '</script><script>const data=' + payload + """;
const canvas=document.getElementById('pet');
const controls=[...document.querySelectorAll('[data-action]')];
const pause=document.getElementById('pause');
const activity=document.getElementById('activity');
DrawToLifePlayer.load(canvas,data.manifest,data.assets).then(p=>{
window.pet=p;
const labels={feed:'¡A comer!',pet:'¡Le encantan los mimos!',play:'¡A jugar!',welcome:'Tu mascota está lista.'};
function sync(){
  controls.forEach(b=>{b.disabled=p.paused||Boolean(p.action);
    b.setAttribute('aria-pressed',String(p.action?.type===b.dataset.action));});
  canvas.setAttribute('aria-disabled',String(p.paused||Boolean(p.action)));
}
canvas.addEventListener('character:actionstart',e=>{sync();activity.textContent=labels[e.detail.action];});
canvas.addEventListener('character:actionend',()=>{sync();activity.textContent='';});
controls.forEach(b=>b.onclick=()=>p[b.dataset.action]());
pause.disabled=false;
pause.onclick=()=>{p.setPaused(!p.paused);sync();
pause.setAttribute('aria-label',p.paused?'Seguir jugando':'Pausar');
pause.setAttribute('aria-pressed',String(p.paused));
pause.innerHTML=p.paused?""" + json.dumps(icon("resume")) + ":" + json.dumps(icon("pause")) + """;};
sync();p.welcome();
window.addEventListener('pagehide',()=>p.destroy(),{once:true});
}).catch(e=>{console.error(e);const error=document.getElementById('error');error.hidden=false;
error.textContent='No pudimos mostrar la mascota. Probá crearla otra vez.';});
</script></body></html>""")


def preview_html(puppet: Puppet) -> str:
    document = html.escape(preview_document(puppet, embedded=True), quote=True)
    return (f'<iframe title="Tu mascota animada" sandbox="allow-scripts" srcdoc="{document}" '
            'style="display:block;width:100%;height:min(740px,calc(100svh - 112px));min-height:400px;border:0"></iframe>')
