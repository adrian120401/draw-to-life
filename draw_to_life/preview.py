"""Preview autosuficiente en iframe: funciona con Gradio 5, sin CDN ni fetch."""

import base64
import html
from io import BytesIO
import json

from .rig import Puppet, player_source
from .scene import DECORATIONS, SCENE_CSS, TOY_BALL, TOY_BUBBLES, TOY_FOOD, icon


def preview_document(puppet: Puppet, *, embedded: bool = False) -> str:
    assets = {}
    for name, texture in puppet.textures.items():
        buffer = BytesIO()
        texture.save(buffer, format="PNG")
        assets[name] = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
    payload = json.dumps({"manifest": puppet.manifest, "assets": assets}, ensure_ascii=True).replace("<", "\\u003c")
    runtime = player_source()
    scene_style = SCENE_CSS
    if embedded:
        # El fondo pertenece a la pantalla completa, no a la caja del iframe.
        scene_style += "html,body{background:transparent}.playroom-shapes{display:none}"
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" href="data:,">'
            '<title>Tu mascota</title><style>' + scene_style + '</style></head><body>'
            + DECORATIONS + '<main class="pet-room"><div class="pet-stage">'
            '<canvas id="pet" role="button" tabindex="0" aria-label="Acariciar a tu mascota" aria-describedby="how-to-play"></canvas>'
            '<button class="toy toy-food" data-tool="food" aria-label="Dar comida" disabled>'
            + TOY_FOOD + '<span>Comida</span></button>'
            '<button class="toy toy-ball" data-tool="ball" aria-label="Lanzar la pelota" disabled>'
            + TOY_BALL + '<span>Pelota</span></button>'
            '<button class="toy toy-bubbles" data-tool="bubbles" aria-label="Jugar a las burbujas" disabled>'
            + TOY_BUBBLES + '<span>Burbujas</span></button>'
            '<div class="bubble-hud" hidden><div class="bubble-progress" role="progressbar" '
            'aria-label="Burbujas reventadas" aria-valuemin="0" aria-valuemax="5" aria-valuenow="0">'
            '<i></i><i></i><i></i><i></i><i></i></div>'
            '<button class="pet-utility" id="bubble-exit" aria-label="Salir de burbujas">'
            + icon("close") + '</button></div>'
            '<div class="bubble-finish" hidden><p>¡Lo hiciste!</p><div>'
            '<button id="bubble-replay">Otra vez</button><button id="bubble-back">Volver</button></div></div>'
            '<div class="scene-utilities"><button class="pet-utility" id="sound" aria-label="Silenciar sonidos" aria-pressed="false" disabled>'
            + icon("sound") + '</button><button class="pet-utility" id="pause" aria-label="Pausar" aria-pressed="false" disabled>'
            + icon("pause") + '</button></div></div>'
            '<p id="how-to-play" class="sr-only">Arrastrá la fruta hasta la boca o lanzá la pelota. '
            'Tocá Guardar o devolvé la pelota a su lugar para terminar. '
            'Acariciá la cabeza y frotá la pancita. Tocá Burbujas y reventá cinco para festejar. '
            'Con teclado, usá Tab y Enter en las burbujas, o Escape para salir. '
            'En juego libre, Enter da mimos y las flechas lanzan la pelota.</p>'
            '<p id="activity" class="sr-only" role="status" aria-live="polite"></p>'
            '<p id="error" class="pet-error" role="alert" hidden></p></main><script>'
            + runtime + '</script><script>const data=' + payload + """;
const canvas=document.getElementById('pet');
const controls=[...document.querySelectorAll('[data-tool]')];
const pause=document.getElementById('pause');
const sound=document.getElementById('sound');
const activity=document.getElementById('activity');
const bubbleHud=document.querySelector('.bubble-hud');
const bubbleProgress=document.querySelector('.bubble-progress');
const bubbleFinish=document.querySelector('.bubble-finish');
const bubbleExit=document.getElementById('bubble-exit');
const bubbleReplay=document.getElementById('bubble-replay');
const bubbleBack=document.getElementById('bubble-back');
DrawToLifePlayer.load(canvas,data.manifest,data.assets).then(p=>{
window.pet=p;
const labels={feed:'¡A comer!',pet:'¡Le encantan los mimos!',play:'¡A jugar!',welcome:'Tu mascota está lista.',tickle:'¡Cosquillas!',kick:'¡Otra vez!',rest:'Pelota guardada.',bubblestart:'Reventá cinco burbujas.',celebrate:'¡Cinco de cinco! ¡Lo hiciste!',bubbleend:'Volviste a jugar con tu mascota.'};
function sync(){
  const game=p.scene.bubbles, inGame=game.phase!=='idle';
  p.stage.dataset.bubbleMode=String(inGame);
  controls.forEach(b=>{b.disabled=p.paused||(b.dataset.tool==='food'&&p.scene.food.state==='eating');});
  const ball=controls.find(b=>b.dataset.tool==='ball');
  ball.setAttribute('aria-label',p.scene.ball.active?'Guardar la pelota':'Lanzar la pelota');
  ball.setAttribute('aria-pressed',String(p.scene.ball.active));
  ball.querySelector('span').textContent=p.scene.ball.active?'Guardar':'Pelota';
  bubbleHud.hidden=!inGame;
  bubbleFinish.hidden=!['celebrating','complete'].includes(game.phase);
  bubbleProgress.setAttribute('aria-valuenow',String(game.hits));
  [...bubbleProgress.children].forEach((dot,i)=>dot.dataset.filled=String(i<game.hits));
  bubbleReplay.disabled=p.paused;
  canvas.setAttribute('aria-label',inGame?'Juego de burbujas':'Acariciar a tu mascota');
  canvas.setAttribute('aria-disabled',String(p.paused));
}
canvas.addEventListener('character:actionstart',e=>{sync();if(labels[e.detail.action])activity.textContent=labels[e.detail.action];});
canvas.addEventListener('character:actionend',()=>{sync();activity.textContent='';});
canvas.addEventListener('character:interaction',e=>{sync();
  if(e.detail.interaction==='bubblepop')activity.textContent=p.scene.bubbles.hits+' de 5.';
  else if(labels[e.detail.interaction])activity.textContent=labels[e.detail.interaction];});
controls.forEach(b=>b.onclick=e=>{
  if(b.dataset.tool==='bubbles'){p.sound.unlock();p.startBubbles();if(e.detail===0)p.focusBubble();}
  else if(e.detail===0){p.sound.unlock();b.dataset.tool==='food'?p.feed():p.toggleBall();}
});
bubbleExit.onclick=bubbleBack.onclick=()=>p.stopBubbles();
bubbleReplay.onclick=e=>{p.sound.unlock();p.startBubbles();if(e.detail===0)p.focusBubble();};
pause.disabled=false;sound.disabled=false;
sound.onclick=()=>{p.setMuted(!p.sound.muted);
sound.setAttribute('aria-label',p.sound.muted?'Activar sonidos':'Silenciar sonidos');
sound.setAttribute('aria-pressed',String(p.sound.muted));
sound.innerHTML=p.sound.muted?""" + json.dumps(icon("mute")) + ":" + json.dumps(icon("sound")) + """;};
pause.onclick=()=>{p.setPaused(!p.paused);sync();
if(!p.paused)p.sound.unlock();
pause.setAttribute('aria-label',p.paused?'Seguir jugando':'Pausar');
pause.setAttribute('aria-pressed',String(p.paused));
pause.innerHTML=p.paused?""" + json.dumps(icon("resume")) + ":" + json.dumps(icon("pause")) + """;};
sync();p.welcome();
window.addEventListener('pagehide',e=>{if(e.persisted)p.setPaused(true);else p.destroy();});
}).catch(e=>{console.error(e);const error=document.getElementById('error');error.hidden=false;
error.textContent='No pudimos mostrar la mascota. Probá crearla otra vez.';});
</script></body></html>""")


def preview_html(puppet: Puppet) -> str:
    document = html.escape(preview_document(puppet, embedded=True), quote=True)
    return (f'<iframe title="Tu mascota animada" sandbox="allow-scripts" srcdoc="{document}" '
            'style="display:block;width:100%;height:min(850px,calc(100svh - 88px));min-height:420px;border:0"></iframe>')
