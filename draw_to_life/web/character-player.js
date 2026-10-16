/* Reproductor portátil. Animaciones e interacciones sin red ni inferencia. */
(function (root) {
  "use strict";
  const identity = () => [1, 0, 0, 1, 0, 0];
  const durations = {feed: 3.6, pet: 2.2, play: 2.8, welcome: 1.3};
  const clamp = value => Math.max(0, Math.min(1, value));
  function multiply(a, b) {
    return [a[0]*b[0]+a[2]*b[1], a[1]*b[0]+a[3]*b[1],
      a[0]*b[2]+a[2]*b[3], a[1]*b[2]+a[3]*b[3],
      a[0]*b[4]+a[2]*b[5]+a[4], a[1]*b[4]+a[3]*b[5]+a[5]];
  }
  function around(pivot, angle, sx, sy, dy = 0) {
    const c = Math.cos(angle), s = Math.sin(angle), [x, y] = pivot;
    return [c*sx, s*sx, -s*sy, c*sy, x-c*sx*x+s*sy*y, y+dy-s*sx*x-c*sy*y];
  }
  function actionPose(action, seconds) {
    if (!action || !durations[action.type]) return null;
    const elapsed = seconds - action.start;
    const duration = durations[action.type];
    if (elapsed < 0 || elapsed >= duration) return null;
    const progress = elapsed / duration;
    let mouth = "happy", eyes = "happy";
    if (action.type === "feed" && elapsed < 1.2) {mouth = "open"; eyes = null;}
    else if (action.type === "feed" && elapsed < 2.8) {
      mouth = Math.floor(elapsed * 7) % 2 ? "chew" : "open";
      eyes = null;
    }
    return {type: action.type, elapsed, progress, mouth, eyes,
      envelope: Math.sin(Math.PI * progress)};
  }
  function frame(manifest, seconds, reactionStart = -Infinity, reduced = false, action = null) {
    const {idle, blink, react} = manifest.animations;
    const phase = seconds * 2*Math.PI/idle.duration;
    const elapsed = seconds-reactionStart;
    const reaction = !reduced && elapsed >= 0 && elapsed < react.duration
      ? Math.sin(Math.PI*elapsed/react.duration) : 0;
    const pose = actionPose(action, seconds);
    // Pausas desiguales, deterministas para que sean reproducibles.
    const intervals = [1, 1.27, .86, 1.12].map(value => value * blink.interval);
    let blinkTime = seconds % intervals.reduce((a, b) => a+b, 0);
    for (const interval of intervals) {
      if (blinkTime < interval) break;
      blinkTime -= interval;
    }
    const eyeScale = !reduced && blinkTime < blink.duration
      ? Math.max(.06, Math.abs(2*blinkTime/blink.duration-1)) : 1;
    const lookup = new Map(manifest.layers.map(layer => [layer.id, layer]));
    const result = new Map(), visiting = new Set();
    function resolve(id) {
      if (result.has(id)) return result.get(id);
      if (visiting.has(id)) throw new Error("Ciclo en las uniones del personaje");
      const layer = lookup.get(id);
      if (!layer) throw new Error("Falta una pieza del personaje");
      visiting.add(id);
      let angle = 0, sx = 1, sy = 1, dy = 0;
      if (!reduced) {
        const energy = pose ? pose.envelope : 0;
        if (layer.motion === "breathe") {
          sy += idle.breath_scale*Math.sin(phase);
          dy -= reaction*react.jump*manifest.canvas[1];
          if (pose?.type === "play") {
            const bounce = Math.abs(Math.sin(pose.progress * Math.PI * 3)) * energy;
            dy -= bounce * manifest.canvas[1] * .07;
            sx += bounce * .025; sy -= bounce * .025;
            angle = Math.sin(pose.progress * Math.PI * 6) * energy * .055;
          } else if (pose?.type === "welcome") dy -= energy * manifest.canvas[1] * .025;
        } else if (layer.motion === "head") {
          angle = (idle.head_degrees*Math.sin(phase)+reaction*react.tilt_degrees)*Math.PI/180;
          if (pose?.type === "pet") angle += energy * .1;
          if (pose?.type === "feed") angle += Math.sin(pose.elapsed * 16) * energy * .012;
          if (pose?.type === "welcome") angle -= energy * .08;
        } else if (layer.motion === "sway") {
          angle = (2*Math.sin(phase)+reaction*7+energy*Math.sin(seconds*9)*6)*Math.PI/180;
          if (/right/.test(layer.id)) angle *= -1;
        } else if (layer.motion === "blink" && !pose?.eyes)
          sy = layer.expressions?.closed && eyeScale < .25 ? 1 : eyeScale;
        else if (layer.motion === "smile" && !layer.expressions) sy += reaction*.18;
      }
      const parent = layer.parent ? resolve(layer.parent) : identity();
      const matrix = multiply(parent, around(layer.pivot, angle, sx, sy, dy));
      result.set(id, matrix);
      visiting.delete(id);
      return matrix;
    }
    for (const layer of manifest.layers) resolve(layer.id);
    return {matrices: result, reaction, eyeScale, pose};
  }
  function transformPoint(matrix, point) {
    return [matrix[0]*point[0]+matrix[2]*point[1]+matrix[4],
      matrix[1]*point[0]+matrix[3]*point[1]+matrix[5]];
  }

  class Player {
    constructor(canvas, manifest, images) {
      this.canvas = canvas;
      this.context = canvas.getContext("2d");
      if (!this.context) throw new Error("Canvas 2D no está disponible");
      this.manifest = manifest;
      this.images = images;
      this.elapsed = .5;
      this.reactionStart = -Infinity;
      this.action = null;
      this.paused = false;
      this.destroyed = false;
      this.last = null;
      this.reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
      this.reduced = this.reducedQuery.matches;
      canvas.width = manifest.canvas[0];
      canvas.height = manifest.canvas[1];
      this.hitMasks = new Map();
      for (const layer of manifest.layers) {
        const surface = document.createElement("canvas");
        surface.width = canvas.width; surface.height = canvas.height;
        const ctx = surface.getContext("2d");
        ctx.drawImage(images.get(layer.id), 0, 0);
        this.hitMasks.set(layer.id, ctx.getImageData(0, 0, canvas.width, canvas.height).data);
      }
      this.onPointer = event => {
        const rect = canvas.getBoundingClientRect();
        const x = (event.clientX-rect.left)*canvas.width/rect.width;
        const y = (event.clientY-rect.top)*canvas.height/rect.height;
        const hit = this.manifest.layers.some(layer => {
          const m = this.current.matrices.get(layer.id);
          const determinant = m[0]*m[3]-m[1]*m[2];
          if (Math.abs(determinant) < 1e-10) return false;
          const lx = (m[3]*(x-m[4])-m[2]*(y-m[5]))/determinant;
          const ly = (-m[1]*(x-m[4])+m[0]*(y-m[5]))/determinant;
          const mask = this.hitMasks.get(layer.id);
          return lx >= 0 && ly >= 0 && lx < canvas.width && ly < canvas.height &&
            mask[(Math.floor(ly)*canvas.width+Math.floor(lx))*4+3] > 40;
        });
        if (hit) this.react();
      };
      this.onKey = event => {
        if (event.code === "Space" || event.code === "Enter") {event.preventDefault(); this.react();}
      };
      this.onReduced = event => {this.reduced = event.matches; this.render();};
      this.onVisibility = () => {this.last = null;};
      canvas.addEventListener("pointerdown", this.onPointer);
      canvas.addEventListener("keydown", this.onKey);
      this.reducedQuery.addEventListener("change", this.onReduced);
      document.addEventListener("visibilitychange", this.onVisibility);
      this.render();
      this.tick = now => {
        if (this.destroyed) return;
        if (!this.paused && !document.hidden && this.last !== null) {
          // El reloj sigue para liberar las acciones con movimiento reducido.
          if (!this.reduced || this.action) {
            this.elapsed += Math.min((now-this.last)/1000, .1);
            if (this.action && !actionPose(this.action, this.elapsed)) {
              const type = this.action.type;
              this.action = null;
              this.emit("actionend", {action: type});
            }
            this.render();
          }
        }
        this.last = now;
        this.raf = requestAnimationFrame(this.tick);
      };
      this.raf = requestAnimationFrame(this.tick);
    }
    emit(name, detail = {}) {
      this.canvas.dispatchEvent(new CustomEvent(`character:${name}`, {detail: {id: this.manifest.id, ...detail}}));
    }
    startAction(type) {
      if (this.destroyed || this.paused || this.action || !durations[type]) return false;
      this.action = {type, start: this.elapsed};
      this.emit("actionstart", {action: type});
      this.render();
      return true;
    }
    feed() {return this.startAction("feed");}
    pet() {return this.startAction("pet");}
    play() {return this.startAction("play");}
    welcome() {return this.startAction("welcome");}
    react() {
      if (!this.pet()) return false;
      this.reactionStart = this.elapsed;
      this.emit("react");
      return true;
    }
    setPaused(value) {
      this.paused = Boolean(value); this.last = null;
      this.emit("pause", {paused: this.paused});
    }
    mouthPosition() {
      const layer = this.manifest.layers.find(item => item.motion === "smile");
      if (!layer) return [this.canvas.width*.5, this.canvas.height*.55];
      return transformPoint(this.current.matrices.get(layer.id), layer.mouth_anchor || layer.pivot);
    }
    render() {
      this.current = frame(this.manifest, this.elapsed, this.reactionStart, this.reduced, this.action);
      const ctx = this.context;
      const {pose, eyeScale} = this.current;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      const w = this.canvas.width, h = this.canvas.height;
      ctx.fillStyle = "#63419b18";
      ctx.beginPath(); ctx.ellipse(w*.5, h*.91, w*.2, h*.021, 0, 0, 2*Math.PI); ctx.fill();
      for (const layer of this.manifest.layers) {
        let expression = null;
        if (layer.motion === "smile") expression = pose?.mouth;
        if (layer.motion === "blink") expression = pose?.eyes || (eyeScale < .25 ? "closed" : null);
        const key = expression && layer.expressions?.[expression] ? `${layer.id}__${expression}` : layer.id;
        ctx.setTransform(...this.current.matrices.get(layer.id));
        ctx.drawImage(this.images.get(key), 0, 0);
      }
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      if (pose?.type === "feed" && pose.elapsed < 1.2) {
        const t = clamp(pose.elapsed/1.2), eased = 1-Math.pow(1-t, 3);
        const [mx, my] = this.mouthPosition();
        const x = this.reduced ? mx : w*.77+(mx-w*.77)*eased;
        const y = this.reduced ? my+h*.1 : h*.82+(my-h*.82)*eased-Math.sin(t*Math.PI)*h*.08;
        const size = w*.047*(1-.88*Math.pow(t, 5));
        ctx.save(); ctx.translate(x, y); ctx.rotate(this.reduced ? 0 : -.3+t*.6);
        ctx.fillStyle = "#F07D91";
        ctx.beginPath(); ctx.ellipse(-size*.3, 0, size*.65, size*.85, -.2, 0, Math.PI*2);
        ctx.ellipse(size*.3, 0, size*.65, size*.85, .2, 0, Math.PI*2); ctx.fill();
        ctx.strokeStyle = "#70503F"; ctx.lineWidth = Math.max(2, w*.006);
        ctx.beginPath(); ctx.moveTo(0, -size*.65); ctx.lineTo(size*.12, -size*1.12); ctx.stroke();
        ctx.fillStyle = "#67AD84"; ctx.beginPath();
        ctx.ellipse(size*.42, -size*.95, size*.43, size*.2, -.4, 0, Math.PI*2); ctx.fill(); ctx.restore();
      }
      if (pose && !this.reduced && (pose.type === "pet" || pose.type === "feed" && pose.elapsed > 2.8)) {
        ctx.save();
        for (let i = 0; i < 3; i++) {
          const t = (pose.progress*1.7+i*.28)%1;
          const x = w*(.28+i*.22), y = h*(.4-t*.2), s = w*.023;
          ctx.globalAlpha = Math.sin(t*Math.PI)*.85;
          ctx.fillStyle = "#DE76A8"; ctx.beginPath(); ctx.moveTo(x, y+s*.4);
          ctx.bezierCurveTo(x-s*2, y-s*.6, x-s*.7, y-s*1.6, x, y-s*.7);
          ctx.bezierCurveTo(x+s*.7, y-s*1.6, x+s*2, y-s*.6, x, y+s*.4); ctx.fill();
        }
        ctx.restore();
      }
    }
    destroy() {
      this.destroyed = true;
      cancelAnimationFrame(this.raf);
      this.canvas.removeEventListener("pointerdown", this.onPointer);
      this.canvas.removeEventListener("keydown", this.onKey);
      this.reducedQuery.removeEventListener("change", this.onReduced);
      document.removeEventListener("visibilitychange", this.onVisibility);
      this.images.clear(); this.hitMasks.clear(); this.action = null;
    }
    static async load(canvas, source, assets = null) {
      let manifest, base;
      if (typeof source === "string") {
        base = new URL(source, document.baseURI);
        const response = await fetch(base);
        if (!response.ok) throw new Error("No se pudo cargar character.json");
        manifest = await response.json();
      } else {manifest = source; base = new URL(document.baseURI);}
      if (manifest.schema_version !== 1 || !Array.isArray(manifest.layers))
        throw new Error("Formato de personaje incompatible");
      const entries = manifest.layers.flatMap(layer => [[layer.id, layer.texture],
        ...Object.entries(layer.expressions || {}).map(([name, path]) => [`${layer.id}__${name}`, path])]);
      const loaded = await Promise.all(entries.map(async ([key, path]) => {
        const image = new Image();
        image.src = assets ? assets[key] : new URL(path, base).href;
        await image.decode();
        if (image.width !== manifest.canvas[0] || image.height !== manifest.canvas[1])
          throw new Error("La textura no coincide con el lienzo");
        return [key, image];
      }));
      return new Player(canvas, manifest, new Map(loaded));
    }
  }
  Player.frame = frame;
  Player.multiply = multiply;
  Player.actionPose = actionPose;
  Player.transformPoint = transformPoint;
  root.DrawToLifePlayer = Player;
  if (typeof module !== "undefined" && module.exports) module.exports = Player;
})(typeof globalThis !== "undefined" ? globalThis : window);
