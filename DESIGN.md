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
  food: "#fbe3af"
  food-ink: "#805026"
  affection: "#f7cee0"
  affection-ink: "#933c68"
  play: "#cfe9dc"
  play-ink: "#316c56"
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
    fontSize: "14px"
    fontWeight: 700
  utility:
    fontFamily: "Trebuchet MS, sans-serif"
    fontSize: "14px"
    fontWeight: 400
rounded:
  action: "22px"
  tile: "24px"
  tile-mobile: "21px"
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
  action-food:
    backgroundColor: "{colors.food}"
    textColor: "{colors.food-ink}"
    rounded: "{rounded.tile}"
    width: "72px"
    height: "68px"
  action-affection:
    backgroundColor: "{colors.affection}"
    textColor: "{colors.affection-ink}"
    rounded: "{rounded.tile}"
    width: "72px"
    height: "68px"
  action-play:
    backgroundColor: "{colors.play}"
    textColor: "{colors.play-ink}"
    rounded: "{rounded.tile}"
    width: "72px"
    height: "68px"
  button-pause:
    backgroundColor: "{colors.cream}"
    textColor: "{colors.ink}"
    rounded: "{rounded.circle}"
    size: "44px"
  photo-token:
    backgroundColor: "{colors.cream}"
    rounded: "{rounded.tile}"
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

The interface uses local Trebuchet typography, minimal Rioplatense Spanish and recognizable outline drawings. Movement gives the existing character affection and personality while preserving its anatomy.

**Key Characteristics:**
- Open lilac space with peripheral geometric decoration.
- Soft cream objects and violet primary actions.
- Large character imagery, short labels and gentle reactions.

## Colors

Pastel surroundings support deeper violet text and controls.

### Primary
- **Violet:** primary upload and retry actions; its darker sibling is the hover treatment.

### Secondary
- **Butter, Pink and Lavender:** stars, circles and organic edge shapes.
- **Food, Affection and Play:** warm yellow, rose and mint action tiles, each paired with its own darker icon color. Keep the text labels in Ink.
- **Orbit:** the soft purple processing object.

### Neutral
- **Lilac:** continuous page background.
- **Cream:** photo token and pause control; **White:** primary button text.
- **Ink:** labels and secondary actions; **Stage:** pale organic backing behind the character.
- **Utility Hover:** subtle tonal feedback for restart and download.

**The Quiet Center Rule.** Decorative geometry frames the edges and leaves the central subject legible.

## Typography

**Body and action font:** Trebuchet MS with local sans-serif fallbacks. The base scene also names Arial Rounded MT Bold as its second fallback.

The type is friendly, direct and compact. The observed hierarchy is action-led; there is no display-heading role to inherit.

- **Action:** bold upload text and processing status; use the action token.
- **Retry:** a smaller bold recovery action.
- **Body:** readable centered errors with relaxed leading.
- **Label:** bold names below the three play tiles; reduces to (13px) on mobile.
- **Utility:** regular-weight restart and download labels.

## Layout

Use a centered single column with generous open space. Upload and processing occupy at least (100svh), with (28px 20px) padding and the large spacing step between elements; that gap becomes the roomy step at the mobile breakpoint (480px).

The playroom uses flex centering and (20px 16px) padding. Its square stage is `min(100%, 520px, calc(100svh - 158px))`; mobile uses `min(100%, 410px, calc(100svh - 142px))` with (12px 8px) room padding. Three actions remain in one row, with `clamp(14px, 5vw, 28px)` gaps. Restart and download share a centered row up to (420px) wide. Separate wide and narrow decorative SVG compositions switch at (480px).

## Elevation & Depth

Depth is soft and ambient. The photo token uses `0 12px 30px #63458113`, the primary action `0 6px 18px #69418d20`, and the play tiles `0 5px 14px #60408012`. The character sits over a pale organic stage; secondary text actions have no shadow. These are diffuse lifts, never hard offset outlines.

## Shapes

Rounded rectangles give actions and the photo object a tactile silhouette. Pause is circular. Organic edge blobs and the uneven oval stage coexist with simple circles and five-point stars. The photo token tilts (-8deg). Outline SVG icons use rounded caps and joins; keep them distinct from text glyphs.

## Components

### Buttons

Primary actions are solid violet, bold and comfortably padded, with a minimum upload width of (224px). Retry is smaller with a minimum width of (180px). Hover darkens violet; disabled upload fades to (0.55). Restart and download are quiet transparent text actions with at least (44px) height and (120px) width.

Focus uses a (3px) solid `#724796` outline offset by (5px). Keep that visible for keyboard interaction.

### Play Actions

Comida, Mimos and Jugar pair an outline icon with an explicit label. Their colored tile sizes and radii are tokenized above; mobile tiles reduce to (66px × 62px). Hover lifts and rotates the tile `translateY(-4px) rotate(-3deg)`; press uses `translateY(1px) scale(.96)`. Transitions last (.18s ease-out). During an action or pause, unavailable controls fade to (0.55); the active pressed action retains full opacity.

### Photo Token and Processing Orbit

The cream photo token is a decorative image cue, not a second upload target. Processing uses a heart in a soft blob, with a short live status below. Its (3s ease-in-out) loop gently rotates, scales and changes the blob silhouette. Status follows real generation phases.

### Character Stage and Pause

The character remains the dominant image. The square canvas supports touch and keyboard affection; a cream circular pause button sits at its top right with a (20px) outline icon. Feed, affection and play reactions use the character's existing layers. Reduced-motion preference removes CSS transitions and animation and suppresses canvas motion while allowing interactions to finish.

## Do's and Don'ts

### Do:
- **Do** keep pastel edge decoration behind the central drawing and controls.
- **Do** pair play icons with short visible labels and preserve clear keyboard focus.
- **Do** honor reduced motion and animate only the character anatomy already present.

### Don't:
- **Don't** replace the playful lilac world with a dashboard or technical workbench.
- **Don't** add hard offset shadows or substitute text glyphs for the outline icons.
- **Don't** introduce display typography absent from the current action-led hierarchy.
