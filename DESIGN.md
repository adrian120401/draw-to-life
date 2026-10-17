---
name: Draw to Life
description: A soft lilac playroom for drawings brought to life.
colors:
  lilac: "#e9dff8"
  violet: "#6c4699"
  violet-hover: "#5d3688"
  ink: "#493366"
  cream: "#fffaf1"
  white: "#ffffff"
  stage: "#f5edfc"
  lavender: "#C7B3EB"
  lavender-light: "#D2C0EE"
  lavender-deep: "#C6B0E6"
  dot-purple: "#B79BDC"
  pink: "#F1ADC8"
  butter: "#F7D88D"
  fruit: "#F07D91"
  fruit-edge: "#BC5676"
  fruit-stem: "#76513F"
  fruit-leaf: "#69AF87"
  fruit-shine: "#FFE0E6"
  ball: "#7CC8A9"
  ball-ink: "#376D5C"
  ball-shine: "#C9F0DF"
  reaction-heart: "#DE76A8"
  orbit: "#ccb1ec"
  utility-hover: "#dbcbed"
typography:
  action:
    fontFamily: "Trebuchet MS, sans-serif"
    fontSize: "20px"
    fontWeight: 700
  retry:
    fontFamily: "Trebuchet MS, sans-serif"
    fontSize: "17px"
    fontWeight: 700
  body:
    fontFamily: "Trebuchet MS, Arial Rounded MT Bold, sans-serif"
    fontSize: "16px"
    lineHeight: 1.5
  label:
    fontFamily: "Trebuchet MS, sans-serif"
    fontSize: "13px"
    fontWeight: 700
  camera:
    fontFamily: "Trebuchet MS, sans-serif"
    fontSize: "16px"
    fontWeight: 700
  utility:
    fontFamily: "Trebuchet MS, sans-serif"
    fontSize: "14px"
    fontWeight: 400
rounded:
  action: "22px"
  photo: "24px"
  circle: "50%"
spacing:
  tight: "8px"
  small: "12px"
  medium: "16px"
  large: "24px"
  roomy: "28px"
components:
  button-primary:
    backgroundColor: "{colors.violet}"
    textColor: "{colors.white}"
    typography: "{typography.action}"
    rounded: "{rounded.action}"
    padding: "19px 30px"
  button-primary-hover:
    backgroundColor: "{colors.violet-hover}"
  button-retry:
    backgroundColor: "{colors.violet}"
    textColor: "{colors.white}"
    typography: "{typography.retry}"
    rounded: "{rounded.action}"
    padding: "14px 24px"
  button-utility:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.utility}"
    padding: "12px 8px"
  button-camera:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.camera}"
    padding: "12px 20px"
  toy-food:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    padding: "0"
    width: "86px"
  toy-ball:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    padding: "0"
    width: "86px"
  toy-bubbles:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    padding: "0"
    width: "86px"
  bubble-target:
    backgroundColor: "transparent"
    rounded: "{rounded.circle}"
  bubble-progress:
    backgroundColor: "{colors.cream}"
    rounded: "{rounded.action}"
    padding: "0 10px"
    height: "44px"
  button-bubble-exit:
    backgroundColor: "{colors.cream}"
    textColor: "{colors.ink}"
    rounded: "{rounded.circle}"
    size: "44px"
  bubble-success:
    textColor: "{colors.ink}"
    typography: "{typography.action}"
  button-bubble-replay:
    backgroundColor: "{colors.violet}"
    textColor: "{colors.cream}"
    rounded: "{rounded.action}"
    padding: "12px 18px"
  button-bubble-back:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.action}"
    padding: "12px 18px"
  button-pause:
    backgroundColor: "{colors.cream}"
    textColor: "{colors.ink}"
    rounded: "{rounded.circle}"
    size: "44px"
  button-sound:
    backgroundColor: "{colors.cream}"
    textColor: "{colors.ink}"
    rounded: "{rounded.circle}"
    size: "44px"
  photo-token:
    backgroundColor: "{colors.cream}"
    rounded: "{rounded.photo}"
    width: "148px"
    height: "170px"
  creating-orbit:
    backgroundColor: "{colors.orbit}"
    size: "112px"
---

# Design System: Draw to Life

## Overview

**Creative North Star: "The Lilac Playroom"**

A spacious, playful world where the drawing is the main event. Pale lilac fills the viewport; soft lavender shapes, pink circles and butter stars gather at its edges. Cream objects and rounded controls feel approachable without competing with the character.

The interface uses local Trebuchet typography, minimal Rioplatense Spanish and recognizable outline drawings. Colored fruit, a ball and a bubble wand sit directly in the character's world. Movement gives the existing character affection and personality while preserving its anatomy; touch receives immediate feedback rather than waiting for a prior reaction to finish.

**Key Characteristics:**
- Open lilac space with peripheral geometric decoration.
- Soft cream objects and violet primary actions.
- Large character imagery, three physical toys and direct touch reactions.

## Colors

Pastel surroundings support deeper violet text and controls.

### Primary
- **Violet:** primary upload and retry actions; its darker sibling is the hover treatment.

### Secondary
- **Butter, Pink and Lavender:** stars, circles and organic edge shapes.
- **Fruit:** rose fruit with a darker edge, brown stem, green leaf and pale highlight; the same rose carries into the dragged canvas fruit.
- **Ball:** mint body with darker seams and a pale highlight; the fill and seams persist when the ball enters the canvas.
- **Bubbles:** translucent lavender, rose and mint reuse the toy palette with cream highlights; the final bubble uses Butter, a violet rim and a star.
- **Reaction Heart:** brief affection feedback above the character.
- **Orbit:** the soft purple processing object.

### Neutral
- **Lilac:** continuous page background.
- **Cream:** photo token, pause and sound controls; **White:** primary button text.
- **Ink:** labels and secondary actions; **Stage:** pale organic backing behind the character.
- **Utility Hover:** subtle tonal feedback for camera, restart and download.

**The Quiet Center Rule.** Decorative geometry frames the edges and leaves the central subject legible.

## Typography

**Body and action font:** Trebuchet MS with local sans-serif fallbacks. The base scene also names Arial Rounded MT Bold as its second fallback.

The type is friendly, direct and compact. The observed hierarchy is action-led; there is no display-heading role to inherit.

- **Action:** bold upload text, processing status and bubble success label; use the action token.
- **Retry:** a smaller bold recovery action.
- **Body:** readable centered errors with relaxed leading.
- **Label:** compact bold names below the three physical toys, at the same size on desktop and mobile.
- **Camera:** bold secondary photo-capture action beneath the gallery action.
- **Utility:** regular-weight restart and download labels.
- **Bubble completion actions:** bold (14px) Otra vez and Volver labels reuse the utility size, with the action weight.

## Layout

Use a centered single column with generous open space. Upload and processing occupy at least (100svh), with (28px 20px) padding and the large spacing step between elements; that gap becomes the roomy step at the mobile breakpoint (480px).

The playroom uses flex centering and (20px 16px) padding. Its taller canvas has a (4:5) aspect ratio. Stage width is `min(100%, 560px, calc((100svh - 40px) * .8))`; mobile uses `min(100%, 410px, calc((100svh - 24px) * .8))` with (12px 8px) room padding. The character is scaled from its visible layer bounds to fit the world and leave room for travel, rather than assuming all drawings fill their source canvas.

Fruit, ball and bubble wand anchor at (18%), (50%) and (82%) across the stage, all at (89%) of its height. Their transparent buttons are (86px) wide with (80px) drawings and (2px) label gaps. Bubble mode hides these toys and places five progress dots and exit at the upper left, separated by (8px); sound and pause remain at the upper right, separated by (10px). The completion message and action row sit at (81%) of stage height. Restart and download share a centered row up to (420px) wide. Separate wide and narrow decorative SVG compositions switch at (480px). The embedded preview fills its container with height `min(850px, calc(100svh - 88px))` and a (420px) minimum.

## Elevation & Depth

Depth is soft and ambient. The photo token uses `0 12px 30px #63458113` and the primary action `0 6px 18px #69418d20`. The character sits over a pale organic stage with a translucent purple ground shadow (`#63419b18`). Each toy drawing carries a shallow elliptical shadow (`#63419b15`), without a containing tile or card. Secondary text actions have no shadow. These are diffuse lifts, never hard offset outlines.

## Shapes

Rounded rectangles give primary actions and the photo object a tactile silhouette. Pause, sound and bubble exit controls are circular. Organic edge blobs and the uneven oval stage coexist with simple circles and five-point stars. The photo token tilts (-8deg). Outline utility SVG icons use rounded caps and joins; keep them distinct from text glyphs. The toys have their own fruit, ball and wand silhouettes, highlights and edges, with transparent hit targets. Bubble progress and completion actions reuse the action radius; bubble targets are circular and transparent over the canvas artwork.

## Components

### Buttons

Primary actions are solid violet, bold and comfortably padded, with a minimum upload width of (224px). Retry is smaller with a minimum width of (180px). Hover darkens violet; disabled upload fades to (0.55). Restart and download are quiet transparent text actions with at least (44px) height and (120px) width.

Focus uses a (3px) solid `#724796` outline offset by (5px). Keep that visible for keyboard interaction.

### Camera Capture

Sacar foto is a quiet bold text action alongside the gallery flow, with a minimum (44px) target height and (150px) width. It uses the browser's native image picker with rear-camera capture requested, then follows the same automatic processing flow as gallery upload. Hover uses Utility Hover. Native camera availability remains browser/device dependent.

### Physical Toys

Comida, Pelota and Burbujas pair SVG objects with short visible labels. Hover brightens the object (`brightness(1.04)`); grab and grabbing cursors reinforce the physical toy treatment without lifting a surrounding tile. Food hides at its home position while being dragged or eaten; the ball's home drawing remains at (0.2) opacity while its live canvas object is active. Disabled controls change cursor without a blanket opacity fade.

Drag fruit to the mouth; a tap or keyboard activation feeds directly. A missed drop returns it home in (.22s), and eating lasts (1.05s). Only food is unavailable during that same fruit's eating state; ball and direct affection remain available. Drag or tap the ball to launch it, then let the character chase and nudge it. Canvas ball physics stay within the stage.

The same ball control stores the active ball: its visible label becomes Guardar, its accessible label becomes Guardar la pelota, and its pressed state becomes true. Tapping or activating that control with the keyboard stores the ball; dragging the live ball back to its home position also stores it. Storage ends the chase and play reaction, returns the character toward the center, and preserves any food interaction. The stored control restores Pelota, Lanzar la pelota and a false pressed state, ready to launch again.

### Bubble Round

Burbujas starts a five-pop round in the same stage, stores the active ball and lets an existing food sequence finish. Up to three floating canvas bubbles have transparent native button targets with at least (44px) width and height. Pointer and touch pop them directly; Tab and Enter activate targets, while Enter or Space on the canvas pops the next bubble. The first four pops give immediate (.45s) pet reactions. The fifth bubble is golden and carries a star.

Five (9px) dots with (1.5px) violet borders and (5px) gaps fill violet as progress advances. Their cream capsule is (44px) tall. Its accessible progressbar exposes zero through five; a polite status announces each pop. The adjacent circular exit uses the existing (44px) utility treatment with a (20px) close icon. Exit, Volver or Escape clears bubbles, progress and celebration and restores focus to Burbujas. There is no countdown, loss state or persistent score.

The fifth pop triggers three happy hops and up to (48) confetti pieces over (2.4s), using the existing pink, butter, mint and lavender palette. ¡Lo hiciste! uses the action type token. Otra vez is violet with cream text; Volver is transparent with Ink text. Both use bold (14px) text, the action radius, (12px 18px) padding and at least (44px) height, with an (8px) gap. Replay resets the round, including its dots and particles. Pause disables bubble targets and replay while keeping exit available. Reduced motion keeps bubbles static and retains happy expressions and completion controls, without hops, bursts or confetti. The wand adds only SVG geometry; generated character artwork stays unchanged.

### Direct Affection

The head receives strokes and the body receives rubbing/tickles through the character's visible layer shapes. A dedicated affection tile is absent. Fast reactions blend or interrupt: affection lasts (.55s), play (.7s), and food (1.05s). Feeding keeps its mouth sequence while concurrent affection and ball play remain responsive. Gaze, anticipation and small expression changes connect gestures to feedback without adding anatomy.

### Photo Token and Processing Orbit

The cream photo token is a decorative image cue, not a second upload target. Processing uses a heart in a soft blob, with a short live status below. Its (3s ease-in-out) loop gently rotates, scales and changes the blob silhouette. Status follows real generation phases.

### Character Stage, Sound and Pause

The character remains the dominant image, with a short (1.05s) welcome reaction. The taller canvas supports touch and keyboard affection: Enter or Space gives affection and arrow keys launch the ball. Toy buttons offer native keyboard activation. Screen-reader instructions and a polite live status communicate interactions.

Cream circular sound and pause controls use (20px) outline icons, explicit accessible labels and pressed states. Pause stops simulation, cancels an active drag and stops sound; resuming continues play. Sound starts only after a gesture and uses brief local synthesized tones (up to .19s), with a mute toggle. There is no audio network dependency.

Reduced motion removes CSS transitions/animation and suppresses canvas bounce, chase, ball travel and heart particles while retaining expressions and completed interactions. Animation uses a single frame loop, cached textures and hit masks, with bounded canvas feedback and no per-interaction inference or network request.

## Do's and Don'ts

### Do:
- **Do** keep pastel edge decoration behind the central drawing and controls.
- **Do** pair the three physical toys with short visible labels and preserve clear keyboard focus.
- **Do** keep affection on the character and let new gestures blend or interrupt existing reactions.
- **Do** honor reduced motion and animate only the character anatomy already present.

### Don't:
- **Don't** replace the playful lilac world with a dashboard or technical workbench.
- **Don't** add hard offset shadows or substitute text glyphs for the outline icons.
- **Don't** introduce display typography absent from the current action-led hierarchy.
