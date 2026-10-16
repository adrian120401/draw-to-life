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
  assert.equal(Player.actionPose(action, 1.6).mouth, "open");
  const chewing = new Set([2.3, 2.5, 2.7].map(t => Player.actionPose(action, t).mouth));
  assert.deepEqual(chewing, new Set(["open", "chew"]));
  assert.equal(Player.actionPose(action, 4.1).mouth, "happy");
  assert.equal(Player.actionPose(action, 4.1).eyes, "happy");
  assert.equal(Player.actionPose(action, 4.7), null);
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
    const pose = Player.frame(rig, 1.6, -Infinity, true, {type, start: 1});
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

test("actions reject overlapping, paused and destroyed requests", () => {
  const player = Object.create(Player.prototype);
  Object.assign(player, {elapsed: 1, paused: false, destroyed: false, action: null, emit() {}, render() {}});
  assert.equal(player.feed(), true);
  assert.equal(player.play(), false);
  assert.equal(player.pet(), false);
  player.action = null; player.paused = true;
  assert.equal(player.feed(), false);
  player.paused = false; player.destroyed = true;
  assert.equal(player.pet(), false);
});
