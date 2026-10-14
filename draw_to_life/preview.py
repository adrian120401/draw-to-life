"""Preview autosuficiente en iframe: funciona con Gradio 5, sin CDN ni fetch."""

import base64
import html
from io import BytesIO
import json

from .rig import Puppet, RUNTIME


def preview_document(puppet: Puppet) -> str:
    assets = {}
    for name, texture in puppet.textures.items():
        buffer = BytesIO()
        texture.save(buffer, format="PNG")
        assets[name] = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    payload = json.dumps({"manifest": puppet.manifest, "assets": assets}, ensure_ascii=True).replace("<", "\\u003c")
    runtime = RUNTIME.read_text(encoding="utf-8")
    return """<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{margin:0;background:#fff8e9;color:#514660;font:14px system-ui;text-align:center}
canvas{width:min(100%,360px);height:auto;aspect-ratio:1/1;touch-action:manipulation}
button{background:#7450b7;color:white;border:0;border-radius:18px;padding:8px 18px;cursor:pointer}
p{margin:6px}canvas:focus-visible{outline:3px solid #7450b7}</style>
<canvas id="pet" role="button" tabindex="0" aria-label="Tocar la mascota"></canvas>
<p>¡Tocame para saludar!</p><button id="pause">Pausar</button><p id="error" role="status"></p>
<script>""" + runtime + "</script><script>const data=" + payload + """;
DrawToLifePlayer.load(document.getElementById('pet'),data.manifest,data.assets).then(p=>{
window.pet=p;
document.getElementById('pause').onclick=()=>{p.setPaused(!p.paused);
document.getElementById('pause').textContent=p.paused?'Animar':'Pausar';};
}).catch(e=>{document.getElementById('error').textContent=e.message;});
</script></html>"""


def preview_html(puppet: Puppet) -> str:
    document = html.escape(preview_document(puppet), quote=True)
    return f'<iframe title="Tu mascota animada" sandbox="allow-scripts" srcdoc="{document}" style="width:100%;height:440px;border:0;border-radius:20px"></iframe>'
