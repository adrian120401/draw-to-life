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
