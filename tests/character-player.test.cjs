const test = require("node:test");
const assert = require("node:assert/strict");
const Player = require("../draw_to_life/web/character-player.js");
const rig = {
  canvas: [512, 512],
  layers: [
    {id: "eyes", parent: "head", pivot: [200, 220], motion: "blink"},
    {id: "head", parent: "body", pivot: [256, 290], motion: "head"},
    {id: "body", parent: null, pivot: [256, 440], motion: "breathe"},
  ],
  animations: {
    idle: {duration: 3.2, breath_scale: .018, head_degrees: 1.5},
    blink: {duration: .18, interval: 4.3},
    react: {duration: .85, jump: .025, tilt_degrees: 8},
  },
};
test("parent transforms work even when parents follow children", () => {
  const f = Player.frame(rig, .8);
  assert.equal(f.matrices.size, 3);
  assert.ok(f.matrices.get("body")[3] > 1);
  assert.notDeepEqual(f.matrices.get("eyes"), [1,0,0,1,0,0]);
});
test("blink closes and reopens without removing the eye texture", () => {
  assert.equal(Player.frame(rig, .09).eyeScale, .06);
  assert.equal(Player.frame(rig, .3).eyeScale, 1);
  assert.ok(Player.frame(rig, .09).matrices.get("eyes")[3] > 0);
});
test("reaction ends and returns to the exact idle pose", () => {
  assert.ok(Player.frame(rig, 1.4, 1).reaction > .9);
  assert.deepEqual(Player.frame(rig, 2, 1), Player.frame(rig, 2));
});
test("reduced motion gives a stable pose with eyes open", () => {
  const f = Player.frame(rig, .09, 0, true);
  assert.equal(f.eyeScale, 1);
  assert.equal(f.reaction, 0);
  for (const matrix of f.matrices.values()) assert.deepEqual(matrix, [1,0,0,1,0,0]);
});
test("cycles and missing parents fail clearly", () => {
  const cycle = structuredClone(rig);
  cycle.layers[2].parent = "head";
  assert.throws(() => Player.frame(cycle, 1), /Ciclo/);
  cycle.layers[2].parent = "missing";
  assert.throws(() => Player.frame(cycle, 1), /Falta/);
});
test("animation matrices remain finite through multiple loops", () => {
  for (let time = 0; time < 30; time += .02) {
    for (const m of Player.frame(rig, time, 4).matrices.values()) assert.ok(m.every(Number.isFinite));
  }
});
test("idle repeats with the period declared in the manifest", () => {
  const a = Player.frame(rig, .7), b = Player.frame(rig, .7+rig.animations.idle.duration);
  for (const id of ["body", "head"]) {
    a.matrices.get(id).forEach((value, i) => assert.ok(Math.abs(value-b.matrices.get(id)[i]) < 1e-10));
  }
});

test("feeding opens the mouth, chews, smiles and finishes", () => {
  const action = {type: "feed", start: 1};
  assert.equal(Player.actionPose(action, .5), null);
  assert.equal(Player.actionPose(action, 1.08).mouth, "open");
  const chewing = new Set([1.25, 1.35, 1.45].map(t => Player.actionPose(action, t).mouth));
  assert.deepEqual(chewing, new Set(["open", "chew"]));
  assert.equal(Player.actionPose(action, 1.9).mouth, "happy");
  assert.equal(Player.actionPose(action, 1.9).eyes, "happy");
  assert.equal(Player.actionPose(action, 2.1), null);
});

test("each interaction returns to the exact idle frame without adding limbs", () => {
  for (const type of ["feed", "pet", "play", "welcome"]) {
    assert.deepEqual(Player.frame(rig, 10, -Infinity, false, {type, start: 1}), Player.frame(rig, 10));
    const active = Player.frame(rig, 1.7, -Infinity, false, {type, start: 1});
    assert.equal(active.matrices.size, rig.layers.length);
    for (const m of active.matrices.values()) assert.ok(m.every(Number.isFinite));
  }
});

test("reduced motion keeps facial feedback with stable body transforms", () => {
  for (const type of ["feed", "pet", "play"]) {
    const pose = Player.frame(rig, 1.2, -Infinity, true, {type, start: 1});
    assert.ok(pose.pose.mouth);
    for (const matrix of pose.matrices.values()) assert.deepEqual(matrix, [1,0,0,1,0,0]);
  }
});

test("food targets the mouth after all inherited transforms", () => {
  const manifest = structuredClone(rig);
  manifest.layers.push({id: "mouth", parent: "head", pivot: [256,280], mouth_anchor: [256,290], motion: "smile"});
  const current = Player.frame(manifest, 1.7, -Infinity, false, {type: "play", start: 1});
  const target = Player.prototype.mouthPosition.call({manifest, current});
  assert.deepEqual(target, Player.transformPoint(current.matrices.get("mouth"), [256,290]));
  assert.notDeepEqual(target, [256,290]);
});

test("petting and play stay responsive during feeding; repeated food is rejected", () => {
  const player = Object.create(Player.prototype);
  const scene = new Player.Scene();
  Object.assign(player, {elapsed: 1, scene, paused: false, destroyed: false, action: null,
    sound: {play() {}}, emit() {}, render() {}, mouthPosition() {return [256,280];}});
  scene.onEvent = kind => player.startAction(kind);
  assert.equal(player.feed(), true);
  assert.equal(player.feed(), false);
  assert.equal(player.play(), true);
  assert.equal(player.pet(), true);
  player.action = null; player.paused = true;
  assert.equal(player.feed(), false);
  player.paused = false; player.destroyed = true;
  assert.equal(player.pet(), false);
});

test("food misses and cancelled drags return home without feeding", () => {
  for (const cancelled of [false, true]) {
    const scene = new Player.Scene(), events = [];
    scene.onEvent = type => events.push(type);
    scene.begin("food", scene.foodHome);
    scene.move({x: 30,y: 30});
    scene.end({x: 30,y: 30}, [256,280], 40, cancelled);
    assert.equal(scene.food.state, "return");
    scene.update(.3);
    assert.equal(scene.food.state, "home");
    assert.equal(scene.food.x, scene.foodHome.x);
    assert.deepEqual(events, []);
  }
});

test("food dropped at the mouth is consumed once and respawns in about a second", () => {
  const scene = new Player.Scene(), events = [];
  scene.onEvent = type => events.push(type);
  scene.begin("food", scene.foodHome);
  scene.move({x: 256,y: 280});
  scene.end({x: 256,y: 280}, [256,280], 35);
  assert.equal(scene.food.state,"eating");
  assert.equal(scene.consume([256,280]),false);
  assert.equal(scene.begin("body",{x:256,y:390}),true);
  scene.move({x:280,y:390});
  assert.ok(scene.tickle>0);
  scene.end({x:280,y:390},[256,280],35);
  scene.update(1.1);
  assert.equal(scene.food.state,"home");
  assert.equal(events.filter(e=>e==="feed").length,1);
});

test("ball pursuit, bounces and kicks stay finite and inside the scene for 20 seconds", () => {
  const scene = new Player.Scene(), events = [], positions=[];
  scene.onEvent=kind=>events.push(kind);
  scene.launch();
  for(let i=0;i<1200;i++) {
    scene.update(1/60);
    const b=scene.ball;
    assert.ok([b.x,b.y,b.vx,b.vy,scene.actor.x,scene.actor.vx].every(Number.isFinite));
    assert.ok(b.x>=b.radius && b.x<=scene.width-b.radius);
    assert.ok(b.y>=b.radius && b.y<=scene.ground-b.radius+.001);
    assert.ok(scene.actor.x>=scene.actor.min && scene.actor.x<=scene.actor.max);
    positions.push(scene.actor.x);
  }
  assert.ok(Math.max(...positions)-Math.min(...positions)>30);
  assert.ok(events.includes("kick"));
});

test("cancelled ball capture releases it and ignores a second pointer", () => {
  const scene=new Player.Scene();
  assert.equal(scene.begin("ball",scene.ballHome),true);
  assert.equal(scene.begin("food",scene.foodHome),false);
  scene.move({x:-100,y:900});
  scene.end({x:-100,y:900},[256,280],35,true);
  assert.equal(scene.pointer,null);
  assert.equal(scene.ball.active,false);
  assert.equal(scene.ball.held,false);
  assert.equal(scene.begin("food",scene.foodHome),true);
});

test("tapping the ball tray again stores the ball and ends pursuit", () => {
  const scene=new Player.Scene();
  const trayTap=()=>{scene.begin("ball-home",scene.ballHome);scene.end(scene.ballHome,[256,280],35);};
  trayTap();
  assert.equal(scene.ball.active,true);
  scene.update(.5);
  trayTap();
  assert.equal(scene.ball.active,false);
  assert.equal(scene.ball.held,false);
  for(let i=0;i<180;i++)scene.update(1/60);
  assert.ok(Math.abs(scene.actor.x-scene.width*.5)<.1);
  assert.equal(scene.ball.x,scene.ballHome.x);
  trayTap();
  assert.equal(scene.ball.active,true);
});

test("a live ball can be picked up and dropped back in its tray", () => {
  const scene=new Player.Scene();scene.launch();
  scene.begin("ball",{x:scene.ball.x,y:scene.ball.y});
  scene.move(scene.ballHome);
  scene.end(scene.ballHome,[256,280],35);
  assert.equal(scene.ball.active,false);
  assert.equal(scene.pointer,null);
});

test("reduced motion keeps the actor and ball stable while food and gesture states finish", () => {
  const scene=new Player.Scene(); scene.launch(); scene.consume([256,280]);
  scene.update(.02,true);
  const position=[scene.actor.x,scene.ball.x,scene.ball.y];
  for(let i=0;i<90;i++)scene.update(1/60,true);
  assert.deepEqual([scene.actor.x,scene.ball.x,scene.ball.y],position);
  assert.equal(scene.food.state,"home");
});

test("audio is optional when the browser provides no AudioContext", () => {
  const sound=new Player.Sound();
  assert.doesNotThrow(()=>{sound.unlock();sound.play("feed");sound.setMuted(true);sound.destroy();});
});

test("bubble round stores the ball, rejects duplicate starts and leaves food alone", () => {
  const scene=new Player.Scene();scene.consume([256,280]);scene.launch();
  assert.equal(scene.startBubbles(),true);
  assert.equal(scene.ball.active,false);
  assert.equal(scene.food.state,"eating");
  const ids=scene.bubbles.items.map(b=>b.id);
  assert.equal(scene.startBubbles(),false);
  assert.deepEqual(scene.bubbles.items.map(b=>b.id),ids);
  assert.equal(scene.launch(),false);
  assert.equal(scene.begin("food",scene.foodHome),false);
  assert.equal(scene.consume([256,280]),false);
});

test("five unique bubble hits create one golden finale and one bounded celebration", () => {
  const scene=new Player.Scene(),events=[];scene.onEvent=type=>events.push(type);
  scene.startBubbles();
  for(let hit=0;hit<5;hit++) {
    if(!scene.bubbles.items.length)scene.update(.4);
    const bubble=scene.bubbles.items[0];
    if(hit===4){assert.equal(bubble.golden,true);assert.equal(scene.bubbles.items.length,1);}
    assert.equal(scene.popBubble(bubble.id),true);
    assert.equal(scene.popBubble(bubble.id),false);
    assert.equal(scene.bubbles.hits,hit+1);
  }
  assert.equal(scene.bubbles.phase,"celebrating");
  assert.equal(events.filter(e=>e==="celebrate").length,1);
  assert.equal(scene.bubbles.confetti.length,48);
  scene.update(2.5);
  assert.equal(scene.bubbles.phase,"complete");
  assert.equal(scene.bubbles.confetti.length,0);
  assert.equal(scene.bubbles.items.length,0);
  assert.equal(scene.bubbles.bursts.length,0);
  assert.equal(scene.startBubbles(),true);
  assert.equal(scene.bubbles.hits,0);
  assert.equal(scene.bubbles.round,2);
});

test("misses and old bubble ids do not count and long play stays bounded", () => {
  const scene=new Player.Scene();scene.startBubbles();
  assert.equal(scene.bubbleAt({x:-50,y:-50}),null);
  assert.equal(scene.popBubble(-1),false);
  const old=scene.bubbles.items[0];
  assert.equal(scene.bubbleAt(old).id,old.id);
  scene.popBubble(old.id);scene.stopBubbles();scene.startBubbles();
  assert.equal(scene.popBubble(old.id),false);
  for(let i=0;i<1800;i++) {
    scene.update(1/60);
    assert.ok(scene.bubbles.items.length<=3);
    for(const b of scene.bubbles.items){
      assert.ok([b.x,b.y,b.radius].every(Number.isFinite));
      assert.ok(b.x>b.radius&&b.x<scene.width-b.radius);
      assert.ok(b.y>b.radius&&b.y<scene.ground);
    }
  }
  assert.equal(scene.bubbles.hits,0);
});

test("bubble exit clears every round phase and free play resumes", () => {
  for(const phase of ["playing","celebrating","complete"]) {
    const scene=new Player.Scene();scene.startBubbles();
    scene.bubbles.phase=phase;
    scene.bubbles.confetti.push({x:1});scene.bubbles.bursts.push({born:0});
    assert.equal(scene.stopBubbles(),true);
    assert.equal(scene.bubbles.phase,"idle");
    assert.deepEqual([scene.bubbles.items,scene.bubbles.confetti,scene.bubbles.bursts],[[],[],[]]);
    assert.equal(scene.launch(),true);
    assert.equal(scene.stopBubbles(),false);
  }
});

test("untouched bubbles drift continuously across ten seconds", () => {
  const scene=new Player.Scene();scene.startBubbles();scene.update(9.999);
  const previous=scene.bubbles.items.map(b=>({x:b.x,y:b.y}));
  scene.update(.002);
  scene.bubbles.items.forEach((b,i)=>{
    assert.ok(Math.hypot(b.x-previous[i].x,b.y-previous[i].y)<1);
  });
});

test("reduced-motion bubbles stay still, score normally and finish without confetti", () => {
  const scene=new Player.Scene();scene.startBubbles();scene.update(.02,true);
  const initial=scene.bubbles.items.map(b=>[b.x,b.y]);
  scene.update(2,true);
  assert.deepEqual(scene.bubbles.items.map(b=>[b.x,b.y]),initial);
  for(let i=0;i<5;i++) {
    if(!scene.bubbles.items.length)scene.update(.4,true);
    scene.popBubble(scene.bubbles.items[0].id);scene.update(.01,true);
  }
  assert.equal(scene.bubbles.phase,"celebrating");
  assert.equal(scene.bubbles.confetti.length,0);
  scene.update(2.5,true);
  assert.equal(scene.bubbles.phase,"complete");
  assert.equal(scene.actor.x,scene.width*.5);
});

test("player bubble APIs reject paused and destroyed interactions", () => {
  const player=Object.create(Player.prototype);
  Object.assign(player,{scene:new Player.Scene(),paused:true,destroyed:false,render(){},finishGesture(){}});
  assert.equal(player.startBubbles(),false);
  assert.equal(player.popBubble(1),false);
  player.paused=false;player.destroyed=true;
  assert.equal(player.startBubbles(),false);
  assert.equal(player.popBubble(1),false);
});
