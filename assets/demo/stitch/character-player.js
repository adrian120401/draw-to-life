/* Estado táctil y física en coordenadas del escenario. Sin DOM ni inferencia. */
(function (root) {
  "use strict";
  const clamp = (n, lo, hi) => Math.max(lo, Math.min(hi, n));
  const distance = (a, b) => Math.hypot(a.x-b.x, a.y-b.y);

  class PetScene {
    constructor(width = 512, height = 640) {
      this.width = width; this.height = height; this.time = 0;
      this.ground = height*.72;
      this.actor = {x: width*.5, vx: 0, min: width*.26, max: width*.74};
      this.foodHome = {x: width*.18, y: height*.89};
      this.ballHome = {x: width*.5, y: height*.89};
      this.food = {...this.foodHome, state: "home", since: 0};
      this.ball = {...this.ballHome, vx: 0, vy: 0, radius: width*.054, active: false, held: false, angle: 0};
      this.pointer = null; this.focus = null;
      this.affection = 0; this.tickle = 0; this.petUntil = 0; this.tickleUntil = 0;
      this.kickAt = 0; this.soundAt = 0; this.jump = 0;
      this.bubbles = {phase: "idle", hits: 0, goal: 5, round: 0, nextId: 0,
        items: [], bursts: [], confetti: [], target: null, since: 0, spawnAt: 0};
      this.onEvent = () => {};
    }
    begin(kind, point) {
      if (this.pointer || this.bubbles.phase !== "idle" || kind === "food" && this.food.state === "eating") return false;
      const stowOnTap = kind === "ball-home" && this.ball.active;
      if (kind === "ball-home") kind = "ball";
      this.pointer = {kind, stowOnTap, last: {...point}, start: {...point}, distance: 0, vx: 0, vy: 0, at: this.time};
      this.focus = {...point};
      if (kind === "food") Object.assign(this.food, point, {state: "drag"});
      else if (kind === "ball") Object.assign(this.ball, point, {held: true, active: true, vx: 0, vy: 0});
      else {this.petUntil = this.time+.5; this.affection = .8; this.onEvent("pet");}
      return true;
    }
    move(point) {
      this.focus = {...point};
      const pointer = this.pointer;
      if (!pointer) return;
      const dt = Math.max(1/120, this.time-pointer.at);
      const travelled = distance(point, pointer.last);
      pointer.distance += travelled;
      pointer.vx = clamp((point.x-pointer.last.x)/dt, -this.width*3, this.width*3);
      pointer.vy = clamp((point.y-pointer.last.y)/dt, -this.height*3, this.height*3);
      pointer.last = {...point}; pointer.at = this.time;
      if (pointer.kind === "food") Object.assign(this.food, point);
      else if (pointer.kind === "ball") Object.assign(this.ball, point);
      else {
        this.petUntil = this.time+.4; this.affection = 1;
        if (pointer.kind === "body" && travelled > this.width*.006) {
          this.tickle = Math.min(1, this.tickle+.3); this.tickleUntil = this.time+.22;
          if (this.time >= this.soundAt) {this.onEvent("tickle"); this.soundAt = this.time+.24;}
        }
      }
    }
    end(point, mouth, radius, cancelled = false) {
      const pointer = this.pointer;
      if (!pointer) return;
      this.pointer = null;
      const tap = pointer.distance < this.width*.018;
      if (pointer.kind === "food") {
        if (!cancelled && (tap || distance(point, {x: mouth[0], y: mouth[1]}) <= radius)) this.consume(mouth);
        else Object.assign(this.food, {state: "return", since: this.time, from: {x: this.food.x, y: this.food.y}});
      } else if (pointer.kind === "ball") {
        this.ball.held = false;
        const backInTray = !tap && distance(point, this.ballHome) < this.width*.1;
        if (cancelled || backInTray || tap && pointer.stowOnTap) this.resetBall();
        else if (tap) this.launch();
        else {
          Object.assign(this.ball, {
            x: clamp(point.x, this.ball.radius, this.width-this.ball.radius),
            y: clamp(point.y, this.ball.radius, this.ground-this.ball.radius),
            vx: this.time-pointer.at < .12 ? pointer.vx : 0,
            vy: this.time-pointer.at < .12 ? pointer.vy : 0,
          });
          this.jump = .6; this.onEvent("play");
        }
      } else if (!cancelled) {this.jump = tap ? .8 : .3; this.petUntil = this.time+.45;}
      this.focus = null;
    }
    consume(mouth) {
      if (this.food.state === "eating" || this.bubbles.phase !== "idle") return false;
      Object.assign(this.food, {state: "eating", since: this.time,
        from: {x: this.food.x, y: this.food.y}, target: [...mouth]});
      this.onEvent("feed");
      return true;
    }
    resetBall() {
      Object.assign(this.ball, this.ballHome, {held: false, active: false, vx: 0, vy: 0, angle: 0});
      this.jump = 0;
      this.onEvent("rest");
    }
    launch() {
      if (this.ball.held || this.bubbles.phase !== "idle") return false;
      Object.assign(this.ball, {x: this.actor.x+this.width*.13, y: this.ground-this.height*.13,
        vx: this.width*.65, vy: -this.height*.7, active: true});
      this.jump = 1; this.onEvent("play");
      return true;
    }
    startBubbles() {
      const game = this.bubbles;
      if (this.pointer || game.phase === "playing") return false;
      if (this.ball.active) this.resetBall();
      Object.assign(game, {phase: "playing", hits: 0, round: game.round+1,
        items: [], bursts: [], confetti: [], target: null, since: this.time, spawnAt: this.time});
      for (let i = 0; i < 3; i++) this.spawnBubble(i);
      this.onEvent("bubblestart"); return true;
    }
    spawnBubble(slot = null, golden = false) {
      const game = this.bubbles;
      if (slot === null) slot = [0, 1, 2].find(i => !game.items.some(b => b.slot === i));
      if (slot === undefined || game.items.length >= 3) return;
      const id = ++game.nextId;
      const baseX = this.width*(golden ? .5 : [.22, .78, .5][slot]);
      const baseY = this.height*(golden ? .27 : [.32, .43, .18][slot]);
      game.items.push({id, slot, golden, baseX, baseY, x: baseX, y: baseY,
        born: this.time, radius: this.width*(golden ? .085 : .07)});
    }
    popBubble(id) {
      const game = this.bubbles;
      const bubble = game.items.find(b => b.id === id);
      if (game.phase !== "playing" || !bubble) return false;
      game.items = game.items.filter(b => b !== bubble);
      game.hits++;
      game.bursts.push({x: bubble.x, y: bubble.y, born: this.time, golden: bubble.golden});
      game.target = {x: bubble.x, y: bubble.y, until: this.time+.65};
      game.spawnAt = this.time+.35;
      this.jump = 1;
      if (game.hits === game.goal) {
        game.phase = "celebrating"; game.since = this.time; game.items = [];
        game.confetti = Array.from({length: 48}, (_, i) => {
          const angle = i*2.39996+game.round, speed = this.width*(.2+(i%7)*.045);
          return {x: this.actor.x, y: this.height*.35,
            vx: Math.cos(angle)*speed, vy: -this.height*(.25+(i%5)*.08), angle, color: i%4};
        });
        this.onEvent("celebrate");
      } else {
        if (game.hits === game.goal-1) {game.items = []; this.spawnBubble(0, true);}
        this.onEvent("bubblepop");
      }
      return true;
    }
    bubbleAt(point, minimumRadius = 0) {
      if (this.bubbles.phase !== "playing") return null;
      return [...this.bubbles.items].reverse().find(b => distance(b, point) <= Math.max(b.radius*1.15, minimumRadius)) || null;
    }
    stopBubbles() {
      const game = this.bubbles;
      if (game.phase === "idle") return false;
      Object.assign(game, {phase: "idle", hits: 0, items: [], bursts: [], confetti: [], target: null});
      this.jump = 0; this.focus = null;
      this.onEvent("bubbleend"); return true;
    }
    updateBubbles(dt, reduced) {
      const game = this.bubbles;
      if (game.phase === "idle") return;
      if (game.phase === "playing") {
        if (game.hits < game.goal-1 && game.items.length < 3 && this.time >= game.spawnAt) {
          this.spawnBubble(); game.spawnAt = this.time+.35;
        }
        for (const bubble of game.items) {
          const age = this.time-bubble.born;
          bubble.x = bubble.baseX+(reduced ? 0 : Math.sin(age*1.4+bubble.id)*this.width*.025);
          bubble.y = bubble.baseY-(reduced ? 0 : Math.sin(age*.15)*this.height*.065);
        }
      } else if (game.phase === "celebrating") {
        if (!reduced) for (const p of game.confetti) {
          p.vy += this.height*.85*dt; p.x += p.vx*dt; p.y += p.vy*dt; p.angle += dt*4;
        }
        else game.confetti = [];
        if (this.time-game.since >= 2.4) {
          game.phase = "complete"; game.confetti = []; this.onEvent("bubblecomplete");
        }
      }
      game.bursts = game.bursts.filter(b => this.time-b.born < .35);
    }
    update(dt, reduced = false) {
      // Subpasos estables incluso si el render baja temporalmente de 60 FPS.
      const steps = Math.max(1, Math.ceil(dt/(1/120)));
      for (let i = 0; i < steps; i++) this.step(dt/steps, reduced);
    }
    step(dt, reduced) {
      this.time += dt;
      this.updateBubbles(dt, reduced);
      this.affection += ((this.time < this.petUntil ? 1 : 0)-this.affection)*(1-Math.exp(-dt*12));
      this.tickle += ((this.time < this.tickleUntil ? 1 : 0)-this.tickle)*(1-Math.exp(-dt*15));
      this.jump *= Math.exp(-dt*5);
      if (this.food.state === "return") {
        const t = clamp((this.time-this.food.since)/.22, 0, 1), k = 1-(1-t)**3;
        this.food.x = this.food.from.x+(this.foodHome.x-this.food.from.x)*k;
        this.food.y = this.food.from.y+(this.foodHome.y-this.food.from.y)*k;
        if (t === 1) Object.assign(this.food, this.foodHome, {state: "home"});
      } else if (this.food.state === "eating" && this.time-this.food.since >= 1.05) {
        Object.assign(this.food, this.foodHome, {state: "home"}); this.jump = .8;
      }
      const b = this.ball;
      if (b.active && !b.held) {
        if (!reduced) {
          b.vy += this.height*2.1*dt; b.x += b.vx*dt; b.y += b.vy*dt;
          b.angle += b.vx*dt/b.radius;
          b.vx *= Math.exp(-dt*.3);
          if (b.x < b.radius || b.x > this.width-b.radius) {
            b.x = clamp(b.x, b.radius, this.width-b.radius); b.vx *= -.82;
          }
          if (b.y > this.ground-b.radius) {
            b.y = this.ground-b.radius; b.vy = -Math.abs(b.vy)*.72;
            if (Math.abs(b.vy) < this.height*.06) b.vy = 0;
          }
          if (b.y < b.radius) {b.y = b.radius; b.vy = Math.abs(b.vy)*.6;}
        } else {b.x = clamp(b.x, b.radius, this.width-b.radius); b.y = this.ground-b.radius; b.vx = 0; b.vy = 0;}
      }
      let target = this.width*.5;
      if (b.active && !reduced) target = clamp(b.x, this.actor.min, this.actor.max);
      const game = this.bubbles;
      if (game.phase === "playing" && !reduced) {
        const bubble = game.target?.until > this.time ? game.target : game.items[0];
        if (bubble) target = clamp(bubble.x, this.actor.min, this.actor.max);
      }
      if (this.pointer?.kind === "food") target = this.actor.x;
      if (reduced) {this.actor.x = this.width*.5; this.actor.vx = 0;}
      else {
        this.actor.vx += ((target-this.actor.x)*28-this.actor.vx*10)*dt;
        this.actor.vx = clamp(this.actor.vx, -this.width*.8, this.width*.8);
        this.actor.x = clamp(this.actor.x+this.actor.vx*dt, this.actor.min, this.actor.max);
      }
      if (!reduced && b.active && !b.held && this.time > this.kickAt &&
          Math.abs(b.x-this.actor.x) < this.width*.17 && b.y > this.ground-this.height*.19) {
        const direction = b.x < this.actor.x ? -1 : 1;
        b.x = clamp(this.actor.x+direction*this.width*.18, b.radius, this.width-b.radius);
        b.vx = direction*this.width*.75; b.vy = -this.height*.6;
        this.kickAt = this.time+.8; this.jump = 1; this.onEvent("kick");
      }
    }
  }

  class PetSound {
    constructor() {this.context = null; this.muted = false; this.voices = new Set(); this.lastAt = -Infinity;}
    unlock() {
      if (this.muted) return;
      try {
        const Audio = root.AudioContext || root.webkitAudioContext;
        if (!Audio) return;
        if (!this.context) this.context = new Audio();
        if (this.context.state === "suspended") this.context.resume().catch(() => {});
      } catch (_) { /* Audio opcional: jugar nunca depende de él. */ }
    }
    play(kind) {
      const ctx = this.context;
      if (this.muted || !ctx || ctx.state !== "running" || ctx.currentTime-this.lastAt < .12 || this.voices.size >= 4) return;
      this.lastAt = ctx.currentTime;
      const notes = {feed: [260, 130], pet: [520, 760], tickle: [620, 950], play: [260, 640], kick: [420, 180],
        bubblepop: [900, 340], celebrate: [523, 1046]};
      const [from, to] = notes[kind] || notes.pet;
      const voice = ctx.createOscillator(), gain = ctx.createGain(), at = ctx.currentTime;
      voice.type = kind === "feed" ? "triangle" : "sine";
      voice.frequency.setValueAtTime(from, at); voice.frequency.exponentialRampToValueAtTime(to, at+.12);
      gain.gain.setValueAtTime(0, at); gain.gain.linearRampToValueAtTime(.055, at+.012);
      gain.gain.exponentialRampToValueAtTime(.0001, at+.17);
      voice.connect(gain); gain.connect(ctx.destination); this.voices.add(voice);
      voice.onended = () => {voice.disconnect(); gain.disconnect(); this.voices.delete(voice);};
      voice.start(at); voice.stop(at+.19);
    }
    stop() {for (const voice of this.voices) {try {voice.stop();} catch (_) { /* Ya terminado. */ }} this.voices.clear();}
    setMuted(value) {this.muted = Boolean(value); if (this.muted) this.stop(); else this.unlock();}
    destroy() {this.stop(); if (this.context) this.context.close().catch(() => {}); this.context = null;}
  }
  PetScene.distance = distance;
  root.DrawToLifeScene = PetScene; root.DrawToLifeSound = PetSound;
  if (typeof module !== "undefined" && module.exports) module.exports = {PetScene, PetSound};
})(typeof globalThis !== "undefined" ? globalThis : window);

/* Reproductor portátil. Animaciones e interacciones sin red ni inferencia. */
(function (root) {
  "use strict";
  const sceneModule = !root.DrawToLifeScene && typeof module !== "undefined" && module.exports ? require("./pet-scene.js") : null;
  const Scene = root.DrawToLifeScene || sceneModule.PetScene;
  const Sound = root.DrawToLifeSound || sceneModule.PetSound;
  const identity = () => [1, 0, 0, 1, 0, 0];
  const durations = {feed: 1.05, pet: .55, play: .7, welcome: 1.05, bubblepop: .45, celebrate: 2.4};
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
    if (action.type === "feed" && elapsed < .18) {mouth = "open"; eyes = null;}
    else if (action.type === "feed" && elapsed < .75) {
      mouth = Math.floor(elapsed * 13) % 2 ? "chew" : "open";
      eyes = null;
    }
    if (action.type === "welcome" && elapsed < .18) eyes = "closed";
    return {type: action.type, elapsed, progress, mouth, eyes,
      envelope: Math.sin(Math.PI * progress)};
  }
  function frame(manifest, seconds, reactionStart = -Infinity, reduced = false, action = null, mood = {}) {
    const {idle, blink, react} = manifest.animations;
    const phase = seconds * 2*Math.PI/idle.duration;
    const elapsed = seconds-reactionStart;
    const reaction = !reduced && elapsed >= 0 && elapsed < react.duration
      ? Math.sin(Math.PI*elapsed/react.duration) : 0;
    let pose = actionPose(action, seconds);
    if (mood.tickle > .12 || mood.affection > .15) pose = {...pose,
      mouth: mood.tickle > .2 ? "open" : pose?.mouth || "happy", eyes: "happy"};
    if (mood.anticipate && pose?.type !== "feed") pose = {...pose, mouth: "open", eyes: null};
    if (mood.celebrating) pose = {...pose, eyes: "happy", mouth: pose?.type === "feed" ? pose.mouth : "happy"};
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
        const energy = pose?.envelope || 0;
        if (layer.motion === "breathe") {
          sy += idle.breath_scale*1.6*Math.sin(phase);
          dy -= reaction*react.jump*manifest.canvas[1];
          if (pose?.type === "play" || pose?.type === "bubblepop") {
            const bounce = Math.sin(pose.progress * Math.PI) * energy;
            dy -= bounce * manifest.canvas[1] * .07;
            sx += bounce * .025; sy -= bounce * .025;
            angle = Math.sin(pose.progress * Math.PI * 2) * energy * .075;
          } else if (pose?.type === "welcome") {
            dy -= energy * manifest.canvas[1] * .025;
            sx += Math.sin(pose.progress*Math.PI*2)*.06;
            sy -= Math.sin(pose.progress*Math.PI*2)*.06;
          }
        } else if (layer.motion === "head") {
          angle = (idle.head_degrees*2*Math.sin(phase)+reaction*react.tilt_degrees)*Math.PI/180;
          angle += (mood.lookX || 0)*.12+(mood.affection || 0)*.12;
          if (pose?.type === "pet") angle += energy * .12;
          if (pose?.type === "feed") angle += Math.sin(pose.elapsed * 25) * energy * .025;
          if (pose?.type === "welcome") angle -= energy * .14;
          if (mood.tickle > .1) angle += Math.sin(seconds*32)*mood.tickle*.09;
        } else if (layer.motion === "sway") {
          angle = (4*Math.sin(phase)+reaction*7+energy*Math.sin(seconds*16)*13+(mood.tickle || 0)*Math.sin(seconds*24)*12)*Math.PI/180;
          if (/right/.test(layer.id)) angle *= -1;
        } else if (layer.motion === "blink" && !pose?.eyes)
          sy = layer.expressions?.closed && eyeScale < .25 ? 1 : eyeScale;
        else if (layer.motion === "smile" && !layer.expressions) sy += reaction*.18;
      }
      const parent = layer.parent ? resolve(layer.parent) : identity();
      const local = around(layer.pivot, angle, sx, sy, dy);
      if (!reduced && layer.motion === "blink") local[4] += (mood.lookX || 0)*manifest.canvas[0]*.008;
      const matrix = multiply(parent, local);
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
      this.elapsed = 0;
      this.reactionStart = -Infinity;
      this.action = null;
      this.paused = false;
      this.destroyed = false;
      this.last = null;
      this.sound = new Sound();
      this.scene = new Scene(manifest.canvas[0], Math.round(manifest.canvas[0]*1.25));
      this.stage = canvas.parentElement;
      this.bubbleTargets = Array.from({length: 3}, (_, slot) => {
        const button = document.createElement("button");
        button.type = "button"; button.className = "bubble-target"; button.hidden = true;
        button.dataset.bubbleSlot = String(slot);
        button.setAttribute("aria-label", "Reventar burbuja");
        this.stage.append(button); return button;
      });
      this.lookX = 0;
      this.gestureId = null;
      this.reducedQuery = matchMedia("(prefers-reduced-motion: reduce)");
      this.reduced = this.reducedQuery.matches;
      canvas.width = this.scene.width;
      canvas.height = this.scene.height;
      this.hitMasks = new Map();
      this.bounds = [manifest.canvas[0], manifest.canvas[1], 0, 0];
      for (const layer of manifest.layers) {
        const surface = document.createElement("canvas");
        surface.width = manifest.canvas[0]; surface.height = manifest.canvas[1];
        const ctx = surface.getContext("2d");
        ctx.drawImage(images.get(layer.id), 0, 0);
        const data = ctx.getImageData(0, 0, surface.width, surface.height).data;
        this.hitMasks.set(layer.id, data);
        for (let y = 0; y < surface.height; y++) for (let x = 0; x < surface.width; x++) {
          if (data[(y*surface.width+x)*4+3] > 40) {
            this.bounds[0] = Math.min(this.bounds[0], x); this.bounds[1] = Math.min(this.bounds[1], y);
            this.bounds[2] = Math.max(this.bounds[2], x+1); this.bounds[3] = Math.max(this.bounds[3], y+1);
          }
        }
      }
      const [left, top, right, bottom] = this.bounds;
      this.scale = Math.min(canvas.width*.65/(right-left), canvas.height*.57/(bottom-top));
      const margin = Math.max(canvas.width*.25, (right-left)*this.scale*.58);
      this.scene.actor.min = margin; this.scene.actor.max = canvas.width-margin;
      this.scene.onEvent = type => {
        if (["rest", "bubblestart", "bubbleend", "bubblecomplete"].includes(type)) {
          if (type === "rest" && this.action?.type === "play" || ["bubbleend", "bubblestart"].includes(type) && ["bubblepop", "celebrate"].includes(this.action?.type)) {
            const action = this.action.type;
            this.action = null;
            this.emit("actionend", {action, interrupted: true});
          }
        } else {
          this.startAction(type === "tickle" ? "pet" : type === "kick" ? "play" : type);
          this.sound.play(type);
        }
        this.emit("interaction", {interaction: type});
      };
      this.point = event => {
        const rect = canvas.getBoundingClientRect();
        return {x: (event.clientX-rect.left)*canvas.width/rect.width,
          y: (event.clientY-rect.top)*canvas.height/rect.height};
      };
      this.onPointer = event => {
        if (this.paused || this.gestureId !== null || event.isPrimary === false || event.button > 0) return;
        const tool = event.target.closest?.('[data-tool]');
        const bubbleTarget = event.target.closest?.('[data-bubble-slot]');
        if (event.target.closest?.('button') && !tool && !bubbleTarget) return;
        if (tool?.dataset.tool === "bubbles") return;
        const point = this.point(event);
        if (this.scene.bubbles.phase === "playing") {
          this.sound.unlock(); event.preventDefault();
          const bubble = bubbleTarget ? this.scene.bubbles.items.find(b => b.slot === Number(bubbleTarget.dataset.bubbleSlot))
            : this.scene.bubbleAt(point, 24*canvas.width/canvas.getBoundingClientRect().width);
          if (bubble) this.popBubble(bubble.id);
          return;
        }
        if (this.scene.bubbles.phase !== "idle") return;
        let kind = tool?.dataset.tool === "ball" ? "ball-home" : tool?.dataset.tool;
        if (!kind && this.scene.ball.active && Math.hypot(point.x-this.scene.ball.x, point.y-this.scene.ball.y) < this.scene.ball.radius*1.7) kind = "ball";
        if (!kind) {
          const layer = this.hitLayer(point);
          if (layer) kind = ["head", "blink", "smile"].includes(layer.motion) || layer.parent === "head" ? "head" : "body";
        }
        this.sound.unlock();
        if (!kind || !this.scene.begin(kind, point)) return;
        event.preventDefault(); this.gestureId = event.pointerId;
        canvas.setPointerCapture(event.pointerId); this.render();
      };
      this.onMove = event => {
        if (this.paused || event.isPrimary === false) return;
        if (this.gestureId !== null && this.gestureId !== event.pointerId) return;
        if (this.gestureId !== null) event.preventDefault();
        this.scene.move(this.point(event));
      };
      this.onUp = event => {
        if (event.pointerId !== this.gestureId) return;
        this.finishGesture(this.point(event), event.type !== "pointerup"); this.render();
      };
      this.onKey = event => {
        if (event.code === "Escape" && this.scene.bubbles.phase !== "idle") {
          event.preventDefault(); this.stopBubbles(); return;
        }
        if (event.target !== canvas) return;
        if (this.scene.bubbles.phase === "playing" && ["Space", "Enter"].includes(event.code)) {
          event.preventDefault(); this.sound.unlock();
          const bubble = this.scene.bubbles.items[0]; if (bubble) this.popBubble(bubble.id);
          return;
        }
        if (event.code === "Space" || event.code === "Enter") {event.preventDefault(); this.sound.unlock(); this.react();}
        else if (event.code === "ArrowLeft" || event.code === "ArrowRight") {
          event.preventDefault(); this.sound.unlock(); this.play(event.code === "ArrowLeft" ? -1 : 1);
        }
      };
      this.onReduced = event => {this.reduced = event.matches; this.render();};
      this.onVisibility = () => {
        this.last = null;
        if (document.hidden) {this.finishGesture(null, true); this.sound.stop();}
      };
      this.onLeave = () => {if (this.gestureId === null) this.scene.focus = null;};
      this.onBubbleClick = event => {
        const target = event.target.closest?.('[data-bubble-slot]');
        if (event.detail !== 0 || !target) return;
        const bubble = this.scene.bubbles.items.find(b => b.slot === Number(target.dataset.bubbleSlot));
        this.sound.unlock(); if (bubble) this.popBubble(bubble.id);
      };
      this.stage.addEventListener("pointerdown", this.onPointer);
      this.stage.addEventListener("pointermove", this.onMove, {passive: false});
      canvas.addEventListener("pointerup", this.onUp);
      canvas.addEventListener("pointercancel", this.onUp);
      canvas.addEventListener("lostpointercapture", this.onUp);
      this.stage.addEventListener("pointerleave", this.onLeave);
      this.stage.addEventListener("keydown", this.onKey);
      this.stage.addEventListener("click", this.onBubbleClick);
      this.reducedQuery.addEventListener("change", this.onReduced);
      document.addEventListener("visibilitychange", this.onVisibility);
      this.render();
      this.tick = now => {
        if (this.destroyed) return;
        if (!this.paused && !document.hidden && this.last !== null) {
            const dt = Math.min((now-this.last)/1000, .05);
            this.elapsed += dt;
            this.scene.update(dt, this.reduced);
            const game = this.scene.bubbles;
            const target = this.scene.focus || (game.phase === "playing" ?
              (game.target?.until > this.scene.time ? game.target : game.items[0]) : null) || (this.scene.ball.active ? this.scene.ball : null);
            const wanted = target ? Math.max(-1, Math.min(1, (target.x-this.scene.actor.x)/(canvas.width*.32))) : Math.sin(this.elapsed*.8)*.2;
            this.lookX += (wanted-this.lookX)*(1-Math.exp(-dt*12));
            if (this.action && !actionPose(this.action, this.elapsed)) {
              const type = this.action.type;
              this.action = null;
              this.emit("actionend", {action: type});
            }
            this.render();
        }
        this.last = now;
        this.raf = requestAnimationFrame(this.tick);
      };
      this.raf = requestAnimationFrame(this.tick);
    }
    emit(name, detail = {}) {
      this.canvas.dispatchEvent(new CustomEvent(`character:${name}`, {detail: {id: this.manifest.id, ...detail}}));
    }
    hitLayer(point) {
      const [width, height] = this.manifest.canvas;
      for (const layer of [...this.manifest.layers].reverse()) {
        const m = this.current.matrices.get(layer.id), det = m[0]*m[3]-m[1]*m[2];
        if (Math.abs(det) < 1e-10) continue;
        const x = (m[3]*(point.x-m[4])-m[2]*(point.y-m[5]))/det;
        const y = (-m[1]*(point.x-m[4])+m[0]*(point.y-m[5]))/det;
        if (x >= 0 && y >= 0 && x < width && y < height &&
            this.hitMasks.get(layer.id)[(Math.floor(y)*width+Math.floor(x))*4+3] > 40) return layer;
      }
      return null;
    }
    finishGesture(point, cancelled) {
      if (this.gestureId === null) return;
      const id = this.gestureId; this.gestureId = null;
      const rect = this.canvas.getBoundingClientRect();
      const radius = Math.max(this.canvas.width*.055, 28*this.canvas.width/rect.width);
      this.scene.end(point || this.scene.pointer?.last || {x: 0, y: 0}, this.mouthPosition(), radius, cancelled);
      if (this.canvas.hasPointerCapture(id)) this.canvas.releasePointerCapture(id);
    }
    startAction(type) {
      if (this.destroyed || this.paused || !durations[type]) return false;
      if (this.action?.type === "feed") return type !== "feed";
      if (this.action) this.emit("actionend", {action: this.action.type, interrupted: true});
      this.action = {type, start: this.elapsed};
      this.emit("actionstart", {action: type});
      this.render();
      return true;
    }
    feed() {
      if (this.destroyed || this.paused) return false;
      return this.scene.consume(this.mouthPosition());
    }
    pet() {
      if (this.destroyed || this.paused) return false;
      this.scene.petUntil = this.scene.time+.55; this.scene.affection = 1;
      this.sound.play("pet"); return this.startAction("pet");
    }
    play(direction = 1) {
      if (this.destroyed || this.paused) return false;
      const result = this.scene.launch();
      this.scene.ball.vx *= direction < 0 ? -1 : 1;
      this.render(); return result;
    }
    toggleBall() {
      if (this.destroyed || this.paused || this.scene.ball.held || this.scene.bubbles.phase !== "idle") return false;
      if (!this.scene.ball.active) return this.play();
      this.scene.resetBall(); this.render(); return true;
    }
    startBubbles() {
      if (this.destroyed || this.paused) return false;
      this.finishGesture(null, true);
      const result = this.scene.startBubbles(); this.render(); return result;
    }
    popBubble(id) {
      if (this.destroyed || this.paused) return false;
      const result = this.scene.popBubble(id); this.render(); return result;
    }
    stopBubbles() {
      if (this.destroyed) return false;
      const result = this.scene.stopBubbles(); this.render();
      this.pendingBubbleFocus = false;
      if (result) this.stage.querySelector('[data-tool="bubbles"]')?.focus({preventScroll: true});
      return result;
    }
    focusBubble() {this.bubbleTargets.find(b => !b.hidden)?.focus({preventScroll: true});}
    welcome() {return this.startAction("welcome");}
    react() {
      if (!this.pet()) return false;
      this.reactionStart = this.elapsed;
      this.emit("react");
      return true;
    }
    setPaused(value) {
      this.finishGesture(null, true);
      this.paused = Boolean(value); this.last = null;
      if (this.paused) this.sound.stop();
      this.render();
      this.emit("pause", {paused: this.paused});
    }
    setMuted(value) {this.sound.setMuted(value); this.emit("mute", {muted: this.sound.muted});}
    mouthPosition() {
      const layer = this.manifest.layers.find(item => item.motion === "smile");
      if (!layer) return [this.canvas.width*.5, this.canvas.height*.55];
      return transformPoint(this.current.matrices.get(layer.id), layer.mouth_anchor || layer.pivot);
    }
    render() {
      const {scene} = this;
      const previousMouth = this.current ? this.mouthPosition() : [this.canvas.width*.5, this.canvas.height*.4];
      const near = scene.food.state === "drag" && Math.hypot(scene.food.x-previousMouth[0], scene.food.y-previousMouth[1]) < this.canvas.width*.22;
      this.current = frame(this.manifest, this.elapsed, this.reactionStart, this.reduced, this.action,
        {lookX: this.lookX, affection: scene.affection, tickle: scene.tickle, anticipate: near,
          celebrating: scene.bubbles.phase === "celebrating"});
      const ctx = this.context;
      const {pose, eyeScale} = this.current;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      const w = this.canvas.width, h = this.canvas.height;
      const moving = Math.min(1, Math.abs(scene.actor.vx)/(w*.25));
      const hop = this.reduced ? 0 : Math.abs(Math.sin(this.elapsed*12))*(moving*.035+scene.jump*.045)*h;
      const happyBounce = !this.reduced && pose?.type === "welcome" ? Math.sin(pose.progress*Math.PI)*h*.035 : 0;
      const celebration = !this.reduced && scene.bubbles.phase === "celebrating" ?
        Math.abs(Math.sin((scene.time-scene.bubbles.since)/2.4*Math.PI*3))*h*.065 : 0;
      const [left, , right, bottom] = this.bounds;
      const sx = this.scale*(this.reduced ? 1 : 1+Math.sin(this.elapsed*12)*moving*.025);
      const world = [sx, 0, 0, this.scale, scene.actor.x-(left+right)*.5*sx,
        scene.ground-bottom*this.scale-hop-happyBounce-celebration];
      for (const [id, matrix] of this.current.matrices) this.current.matrices.set(id, multiply(world, matrix));
      ctx.fillStyle = "#63419b18";
      ctx.beginPath(); ctx.ellipse(scene.actor.x, scene.ground+h*.008, w*.17-hop*.3, h*.016, 0, 0, 2*Math.PI); ctx.fill();
      for (const layer of this.manifest.layers) {
        let expression = null;
        if (layer.motion === "smile") expression = pose?.mouth;
        if (layer.motion === "blink") expression = pose?.eyes || (eyeScale < .25 ? "closed" : null);
        const key = expression && layer.expressions?.[expression] ? `${layer.id}__${expression}` : layer.id;
        ctx.setTransform(...this.current.matrices.get(layer.id));
        ctx.drawImage(this.images.get(key), 0, 0);
      }
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      const foodAge = scene.time-scene.food.since;
      if (scene.food.state !== "home" && (scene.food.state !== "eating" || foodAge < .2)) {
        const t = scene.food.state === "eating" ? (this.reduced ? 1 : clamp(foodAge/.2)) : 0;
        const [mx, my] = this.mouthPosition();
        const from = scene.food.state === "eating" ? scene.food.from : scene.food;
        const x = from.x+(mx-from.x)*t, y = from.y+(my-from.y)*t;
        const size = w*.058*(1-t*.94);
        ctx.save(); ctx.translate(x, y); ctx.rotate(this.reduced ? 0 : -.15);
        ctx.fillStyle = "#F07D91";
        ctx.beginPath(); ctx.ellipse(-size*.3, 0, size*.65, size*.85, -.2, 0, Math.PI*2);
        ctx.ellipse(size*.3, 0, size*.65, size*.85, .2, 0, Math.PI*2); ctx.fill();
        ctx.strokeStyle = "#70503F"; ctx.lineWidth = Math.max(2, w*.006);
        ctx.beginPath(); ctx.moveTo(0, -size*.65); ctx.lineTo(size*.12, -size*1.12); ctx.stroke();
        ctx.fillStyle = "#67AD84"; ctx.beginPath();
        ctx.ellipse(size*.42, -size*.95, size*.43, size*.2, -.4, 0, Math.PI*2); ctx.fill(); ctx.restore();
      }
      if (scene.ball.active) {
        const ball = scene.ball;
        ctx.save(); ctx.translate(ball.x, ball.y); ctx.rotate(this.reduced ? 0 : ball.angle);
        ctx.fillStyle = "#7CC8A9"; ctx.strokeStyle = "#376D5C"; ctx.lineWidth = w*.004;
        ctx.beginPath(); ctx.arc(0, 0, ball.radius, 0, Math.PI*2); ctx.fill(); ctx.stroke();
        ctx.beginPath(); ctx.arc(0, 0, ball.radius*.48, 0, Math.PI*2); ctx.stroke();
        for (let i = 0; i < 3; i++) {
          const a = i*Math.PI*2/3;
          ctx.beginPath(); ctx.moveTo(Math.cos(a)*ball.radius*.5, Math.sin(a)*ball.radius*.5);
          ctx.lineTo(Math.cos(a)*ball.radius, Math.sin(a)*ball.radius); ctx.stroke();
        }
        ctx.restore();
      }
      this.drawBubbles();
      const affectionate = scene.affection > .2 || scene.tickle > .2 || pose?.type === "feed" && pose.elapsed > .75;
      if (affectionate && !this.reduced) {
        ctx.save();
        for (let i = 0; i < 3; i++) {
          const t = (this.elapsed*1.4+i*.28)%1;
          const x = scene.actor.x+w*(-.16+i*.16), y = h*(.34-t*.13), s = w*.023;
          ctx.globalAlpha = Math.sin(t*Math.PI)*.85;
          ctx.fillStyle = "#DE76A8"; ctx.beginPath(); ctx.moveTo(x, y+s*.4);
          ctx.bezierCurveTo(x-s*2, y-s*.6, x-s*.7, y-s*1.6, x, y-s*.7);
          ctx.bezierCurveTo(x+s*.7, y-s*1.6, x+s*2, y-s*.6, x, y+s*.4); ctx.fill();
        }
        ctx.restore();
      }
      const foodAway = String(scene.food.state !== "home"), ballAway = String(scene.ball.active);
      if (this.stage.dataset.foodAway !== foodAway) this.stage.dataset.foodAway = foodAway;
      if (this.stage.dataset.ballAway !== ballAway) this.stage.dataset.ballAway = ballAway;
    }
    drawBubbles() {
      const {scene, context: ctx} = this, game = scene.bubbles, w = scene.width;
      const colors = [["#C7B3EB33", "#6c4699"], ["#F1ADC833", "#BC5676"], ["#7CC8A933", "#376D5C"]];
      for (const b of game.items) {
        const [fill, rim] = b.golden ? ["#F7D88D66", "#6c4699"] : colors[b.slot];
        ctx.save(); ctx.translate(b.x, b.y);
        ctx.fillStyle = fill; ctx.strokeStyle = rim; ctx.lineWidth = w*.0045;
        ctx.beginPath(); ctx.arc(0, 0, b.radius, 0, Math.PI*2); ctx.fill(); ctx.stroke();
        ctx.strokeStyle = "#fffaf1"; ctx.lineWidth = w*.009; ctx.lineCap = "round";
        ctx.beginPath(); ctx.arc(0, 0, b.radius*.72, Math.PI*1.1, Math.PI*1.47); ctx.stroke();
        ctx.fillStyle = "#fffaf1"; ctx.beginPath(); ctx.arc(b.radius*.42, b.radius*.47, w*.007, 0, Math.PI*2); ctx.fill();
        if (b.golden) {
          ctx.fillStyle = "#F7D88D"; ctx.strokeStyle = "#6c4699"; ctx.lineWidth = w*.002;
          ctx.beginPath();
          for (let i = 0; i < 10; i++) {
            const a = i*Math.PI/5-Math.PI/2, r = b.radius*(i%2 ? .23 : .5);
            i ? ctx.lineTo(Math.cos(a)*r, Math.sin(a)*r) : ctx.moveTo(Math.cos(a)*r, Math.sin(a)*r);
          }
          ctx.closePath(); ctx.fill(); ctx.stroke();
        }
        ctx.restore();
      }
      if (!this.reduced) {
        for (const b of game.bursts) {
          const t = (scene.time-b.born)/.35;
          ctx.save(); ctx.globalAlpha = 1-t; ctx.strokeStyle = b.golden ? "#F7D88D" : "#6c4699"; ctx.lineWidth = w*.004;
          for (let i = 0; i < 7; i++) {
            const a = i*Math.PI*2/7, r = w*(.035+t*.08);
            ctx.beginPath(); ctx.moveTo(b.x+Math.cos(a)*r, b.y+Math.sin(a)*r);
            ctx.lineTo(b.x+Math.cos(a)*(r+w*.018), b.y+Math.sin(a)*(r+w*.018)); ctx.stroke();
          }
          ctx.restore();
        }
        const palette = ["#F1ADC8", "#F7D88D", "#7CC8A9", "#C7B3EB"];
        for (const p of game.confetti) {
          ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.angle);
          ctx.globalAlpha = Math.min(1, (2.4-(scene.time-game.since))*2);
          ctx.fillStyle = palette[p.color]; ctx.fillRect(-w*.006, -w*.012, w*.012, w*.024); ctx.restore();
        }
      }
      let lostFocus = false;
      for (let slot = 0; slot < 3; slot++) {
        const button = this.bubbleTargets[slot], b = game.items.find(item => item.slot === slot);
        if (button.hidden !== !b) {
          if (!b && document.activeElement === button) lostFocus = true;
          button.hidden = !b;
        }
        button.disabled = this.paused;
        if (!b) continue;
        button.setAttribute("aria-label", b.golden ? "Reventar la burbuja dorada" : "Reventar burbuja");
        button.style.left = `${b.x/w*100}%`; button.style.top = `${b.y/scene.height*100}%`;
        button.style.width = `${b.radius*2/w*100}%`; button.style.height = `${b.radius*2/scene.height*100}%`;
      }
      if (lostFocus && game.phase === "playing") this.pendingBubbleFocus = true;
      if (this.pendingBubbleFocus && game.phase === "playing" && game.items.length) {
        this.pendingBubbleFocus = false; this.focusBubble();
      }
      if (lostFocus && game.phase === "celebrating") this.stage.querySelector('#bubble-replay')?.focus({preventScroll: true});
    }
    destroy() {
      this.destroyed = true;
      cancelAnimationFrame(this.raf);
      this.finishGesture(null, true); this.sound.destroy();
      this.stage.removeEventListener("pointerdown", this.onPointer);
      this.stage.removeEventListener("pointermove", this.onMove);
      this.stage.removeEventListener("pointerleave", this.onLeave);
      for (const name of ["pointerup", "pointercancel", "lostpointercapture"]) this.canvas.removeEventListener(name, this.onUp);
      this.stage.removeEventListener("keydown", this.onKey);
      this.stage.removeEventListener("click", this.onBubbleClick);
      this.bubbleTargets.forEach(button => button.remove());
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
  Player.Scene = Scene;
  Player.Sound = Sound;
  root.DrawToLifePlayer = Player;
  if (typeof module !== "undefined" && module.exports) module.exports = Player;
})(typeof globalThis !== "undefined" ? globalThis : window);
