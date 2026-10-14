/* Renderer portable, sin red externa ni dependencias de un motor de juegos. */
(function (root) {
  "use strict";
  const identity = () => [1, 0, 0, 1, 0, 0];
  function multiply(a, b) {
    return [a[0]*b[0]+a[2]*b[1], a[1]*b[0]+a[3]*b[1],
      a[0]*b[2]+a[2]*b[3], a[1]*b[2]+a[3]*b[3],
      a[0]*b[4]+a[2]*b[5]+a[4], a[1]*b[4]+a[3]*b[5]+a[5]];
  }
  function around(pivot, angle, sx, sy, dy = 0) {
    const c = Math.cos(angle), s = Math.sin(angle), [x, y] = pivot;
    return [c*sx, s*sx, -s*sy, c*sy, x-c*sx*x+s*sy*y, y+dy-s*sx*x-c*sy*y];
  }
  function frame(manifest, seconds, reactionStart = -Infinity, reduced = false) {
    const {idle, blink, react} = manifest.animations;
    const phase = seconds * 2*Math.PI/idle.duration;
    const elapsed = seconds-reactionStart;
    const reaction = !reduced && elapsed >= 0 && elapsed < react.duration
      ? Math.sin(Math.PI*elapsed/react.duration) : 0;
    const blinkTime = seconds % blink.interval;
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
        if (layer.motion === "breathe") {
          sy += idle.breath_scale*Math.sin(phase);
          dy -= reaction*react.jump*manifest.canvas[1];
        } else if (layer.motion === "head") {
          angle = (idle.head_degrees*Math.sin(phase)+reaction*react.tilt_degrees)*Math.PI/180;
        } else if (layer.motion === "sway") {
          angle = (2*Math.sin(phase)+reaction*7)*Math.PI/180;
          if (/right/.test(layer.id)) angle *= -1;
        } else if (layer.motion === "blink") sy = eyeScale;
        else if (layer.motion === "smile") sy += reaction*.18;
      }
      const parent = layer.parent ? resolve(layer.parent) : identity();
      const matrix = multiply(parent, around(layer.pivot, angle, sx, sy, dy));
      result.set(id, matrix);
      visiting.delete(id);
      return matrix;
    }
    for (const layer of manifest.layers) resolve(layer.id);
    return {matrices: result, reaction, eyeScale};
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
      this.paused = false;
      this.destroyed = false;
      this.last = null;
      this.reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
      this.reduced = this.reducedQuery.matches;
      canvas.width = manifest.canvas[0];
      canvas.height = manifest.canvas[1];
      this.onPointer = event => {
        const rect = canvas.getBoundingClientRect();
        const x = (event.clientX-rect.left)*canvas.width/rect.width;
        const y = (event.clientY-rect.top)*canvas.height/rect.height;
        const hit = this.manifest.layers.some(layer => {
          const m = this.current.matrices.get(layer.id);
          const determinant = m[0]*m[3]-m[1]*m[2];
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
      this.hitMasks = new Map();
      for (const [id, image] of images) {
        const surface = document.createElement("canvas");
        surface.width = canvas.width; surface.height = canvas.height;
        const ctx = surface.getContext("2d");
        ctx.drawImage(image, 0, 0);
        this.hitMasks.set(id, ctx.getImageData(0, 0, canvas.width, canvas.height).data);
      }
      canvas.addEventListener("pointerdown", this.onPointer);
      canvas.addEventListener("keydown", this.onKey);
      this.reducedQuery.addEventListener("change", this.onReduced);
      document.addEventListener("visibilitychange", this.onVisibility);
      this.render();
      this.tick = now => {
        if (this.destroyed) return;
        if (!this.paused && !document.hidden && !this.reduced && this.last !== null) {
          this.elapsed += Math.min((now-this.last)/1000, .1);
          this.render();
        }
        this.last = now;
        this.raf = requestAnimationFrame(this.tick);
      };
      this.raf = requestAnimationFrame(this.tick);
    }
    react() {
      this.reactionStart = this.elapsed;
      this.canvas.dispatchEvent(new CustomEvent("character:react", {detail: {id: this.manifest.id}}));
    }
    setPaused(value) {this.paused = Boolean(value); this.last = null;}
    render() {
      this.current = frame(this.manifest, this.elapsed, this.reactionStart, this.reduced);
      const ctx = this.context;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      for (const layer of this.manifest.layers) {
        ctx.setTransform(...this.current.matrices.get(layer.id));
        ctx.drawImage(this.images.get(layer.id), 0, 0);
      }
      ctx.setTransform(1, 0, 0, 1, 0, 0);
    }
    destroy() {
      this.destroyed = true;
      cancelAnimationFrame(this.raf);
      this.canvas.removeEventListener("pointerdown", this.onPointer);
      this.canvas.removeEventListener("keydown", this.onKey);
      this.reducedQuery.removeEventListener("change", this.onReduced);
      document.removeEventListener("visibilitychange", this.onVisibility);
      this.images.clear(); this.hitMasks.clear();
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
      const loaded = await Promise.all(manifest.layers.map(async layer => {
        const image = new Image();
        image.src = assets ? assets[layer.id] : new URL(layer.texture, base).href;
        await image.decode();
        if (image.width !== manifest.canvas[0] || image.height !== manifest.canvas[1])
          throw new Error("La textura no coincide con el lienzo");
        return [layer.id, image];
      }));
      return new Player(canvas, manifest, new Map(loaded));
    }
  }
  Player.frame = frame;
  Player.multiply = multiply;
  root.DrawToLifePlayer = Player;
  if (typeof module !== "undefined" && module.exports) module.exports = Player;
})(typeof globalThis !== "undefined" ? globalThis : window);
