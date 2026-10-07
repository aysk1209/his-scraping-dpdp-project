---
name: DPDP-compliant HIS extraction — Review demo pages
description: Offline, self-contained demo pages that make a compliance benchmark visible at a glance; the presenter explains.
colors:
  page: "#f5f6f8"
  card: "#ffffff"
  recess: "#f0f2f5"
  line: "#e1e4e9"
  ink: "#14161a"
  ink-soft: "#4d5560"
  ink-quiet: "#686e76"
  ours-blue: "#266ec4"
  agent-violet: "#7d52dd"
  baseline-amber: "#bc7f00"
  good: "#187d43"
  good-wash: "#e1f4e9"
  bad: "#c53232"
  bad-wash: "#fbe5e5"
  warn: "#976419"
  warn-wash: "#fcf1dd"
  on-fill: "#ffffff"
  layer-patient-admin: "#266ec4"
  layer-clinical: "#1baf7a"
  layer-ancillary: "#0e9aa7"
  layer-financial: "#eb6834"
  layer-integration: "#8a6d3b"
  model-a0: "#eb6834"
  model-a1: "#1baf7a"
  model-a2: "#8b5cf6"
  model-a3: "#0e9aa7"
  model-a4: "#d6409f"
  model-a5: "#8a6d3b"
  terminal: "#111316"
  terminal-ink: "#d7dde3"
  terminal-ok: "#5fd38d"
  terminal-no: "#ff7b7b"
  terminal-dim: "#8b949e"
  night-page: "#0f1114"
  night-card: "#181b20"
  night-recess: "#22262c"
  night-line: "#2c3138"
  night-ink: "#eef0f2"
  night-ink-soft: "#a9b1ba"
  night-ink-quiet: "#878e95"
  night-ours-blue: "#4b95ee"
  night-agent-violet: "#a78bfa"
  night-baseline-amber: "#d99a1a"
  night-good: "#3cc279"
  night-good-wash: "#173527"
  night-bad: "#ee6b6b"
  night-bad-wash: "#3a2023"
  night-warn: "#dca13a"
  night-warn-wash: "#3a2f1c"
  night-on-fill: "#0f1114"
  night-layer-clinical: "#22b07e"
  night-layer-ancillary: "#2bb3c0"
  night-layer-financial: "#e0662f"
  night-layer-integration: "#b08a5a"
typography:
  headline:
    fontFamily: "Segoe UI Variable Display, Segoe UI Variable Text, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "2rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.022em"
  key-number:
    fontFamily: "Segoe UI Variable Display, Segoe UI Variable Text, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "1.8rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
    fontFeature: "tnum"
  title:
    fontFamily: "Segoe UI Variable Display, Segoe UI Variable Text, system-ui, -apple-system, Segoe UI, Roboto, sans-serif"
    fontSize: "1.06rem"
    fontWeight: 600
    letterSpacing: "-0.005em"
  subtitle:
    fontFamily: "Segoe UI Variable Text, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif"
    fontSize: "0.9rem"
    fontWeight: 600
  body:
    fontFamily: "Segoe UI Variable Text, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Segoe UI Variable Text, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif"
    fontSize: "0.8rem"
    fontWeight: 400
  data:
    fontFamily: "ui-monospace, Cascadia Mono, Consolas, Courier New, monospace"
    fontSize: "0.8rem"
    fontWeight: 400
    fontFeature: "tnum"
rounded:
  mark: "2px"
  chip: "4px"
  box: "6px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "18px"
  page-bottom: "48px"
components:
  card:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.box}"
    padding: "16px 18px"
  funnel:
    backgroundColor: "{colors.card}"
    rounded: "{rounded.box}"
  funnel-cell:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    typography: "{typography.key-number}"
    padding: "12px 16px"
  sitenav-link:
    textColor: "{colors.ink-soft}"
    padding: "4px 0"
  sitenav-link-current:
    textColor: "{colors.ink}"
    padding: "4px 0"
  step:
    textColor: "{colors.ink-soft}"
    padding: "8px 0"
  step-selected:
    textColor: "{colors.ink}"
    padding: "8px 0"
  seg-button:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink-soft}"
    padding: "4px 11px"
  seg-button-pressed:
    textColor: "{colors.ink}"
    padding: "4px 11px"
  badge:
    backgroundColor: "{colors.recess}"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.chip}"
    padding: "2px 8px"
  badge-good:
    backgroundColor: "{colors.good-wash}"
    textColor: "{colors.good}"
    rounded: "{rounded.chip}"
    padding: "2px 8px"
  badge-bad:
    backgroundColor: "{colors.bad-wash}"
    textColor: "{colors.bad}"
    rounded: "{rounded.chip}"
    padding: "2px 8px"
  badge-warn:
    backgroundColor: "{colors.warn-wash}"
    textColor: "{colors.warn}"
    rounded: "{rounded.chip}"
    padding: "2px 8px"
  chip-fail:
    backgroundColor: "{colors.bad}"
    textColor: "{colors.on-fill}"
    rounded: "{rounded.chip}"
  button-primary:
    backgroundColor: "{colors.ours-blue}"
    textColor: "{colors.on-fill}"
    rounded: "{rounded.box}"
    padding: "5px 12px"
  button-plain:
    backgroundColor: "{colors.page}"
    textColor: "{colors.ink}"
    rounded: "{rounded.box}"
    padding: "5px 12px"
  button-plain-hover:
    backgroundColor: "{colors.recess}"
  tool-button:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.box}"
    height: "2rem"
  select:
    backgroundColor: "{colors.card}"
    textColor: "{colors.ink}"
    rounded: "{rounded.box}"
    padding: "4px 8px"
  track:
    backgroundColor: "{colors.recess}"
    rounded: "{rounded.chip}"
    height: "12px"
  note:
    backgroundColor: "{colors.recess}"
    textColor: "{colors.ink-soft}"
    rounded: "{rounded.box}"
    padding: "8px 12px"
  verdict-ok:
    backgroundColor: "{colors.good-wash}"
    textColor: "{colors.good}"
    rounded: "{rounded.box}"
    padding: "10px 14px"
  verdict-no:
    backgroundColor: "{colors.bad-wash}"
    textColor: "{colors.bad}"
    rounded: "{rounded.box}"
    padding: "10px 14px"
  terminal:
    backgroundColor: "{colors.terminal}"
    textColor: "{colors.terminal-ink}"
    typography: "{typography.data}"
    rounded: "{rounded.box}"
    padding: "8px 10px"
---

# Design System: DPDP-compliant HIS extraction — Review demo pages

## Overview

**Creative North Star: "The Ruled Page"**

Each page reads like a well-set lab report laid on a soft grey desk: white panels with a thin rule round them, a title in a display cut and one line under it, and numbers set large and tabular. Colour marks data (which technique produced a number, which HIS layer a field belongs to, which model a series is, whether a rule held or fell) and one thing more: where you are and what you chose, in our blue. The presenter explains; the page shows the point and lets a panel member click, type or flip a switch.

Density is moderate and laptop-first: one centred 1140px column, a row of plain text links for navigation, a strip of key numbers inside one white panel, then underlined text tabs whose panes hold white panels and tables. Nothing floats and nothing moves on its own except the demos themselves (the portal's sign-in replay and crawl playback, the dataset's retention playback, the assistant's scripted scenes, the login caret). Two themes are equal citizens (system preference, overridable by a header switch), and an A+ switch lifts the root size from 15px to 18px for a projector.

The pages open offline by double-click, so the system is made from what every machine already has: the system's own Segoe UI Variable faces (Display for titles and figures, Text for everything else), a monospace stack, inline SVG icons, inline CSS and script. Minimal, quiet, and a little elegant; never decorated.

**Key Characteristics:**
- Soft grey page, white panels with a 1px rule; no shadows, no gradients, no pills.
- Colour for data (technique, layer, model, verdict) and for the current place and choice, in ours blue.
- States are tinted washes, not outlines: green, red and ochre washes for verdicts, a light blue tint for a selection.
- A display cut for the title, card headings and key figures; the text cut for everything else; mono only for data.
- Navigation and steps are underlined text; the one filled button is the demo's primary action.
- Numbers are written in place; only the demos animate.

## Colors

A cool grey desk with white panels and a small, fixed set of hues; a hue means *who*, *which layer*, *which model*, *what verdict*, or *you are here*.

### Primary
- **Ours Blue** (ours-blue; night-ours-blue in dark): our compliance-aware technique wherever it appears, and the system's working accent: the underline under the current nav link and the selected step (with that step's number), the fill of the primary buttons (Play, Send), the light tint of a selected segment, tile, role or patient (7–12% mixed into the card), the rules page's heat map, focus outlines, links, text selection, caret and form accent.

### Secondary
- **Agent Violet** (agent-violet; night-agent-violet): the publicly available AI agents, as a group.
- **Baseline Amber** (baseline-amber; night-baseline-amber): the coverage-optimised baseline. In the light theme it reaches only 3.4:1 on white, so it colours fills, dots and large figures (1.4rem at 600 and up), never small text.

### Tertiary
- **Verdict Green / Red / Ochre** (good, bad, warn, each with a wash): held / fell / caution. Badges, pills, category chips, rule chips, field chips, verdict bars and matrix cells take the wash as background with text in the solid hue and no border. A failure that matters (a fallen trap cell, an out-of-scope field, a failed rule) is a solid red fill with on-fill text. A declined answer and a closed gate row sit on the red wash.
- **Layer hues** (layer-patient-admin, layer-clinical, layer-ancillary, layer-financial, layer-integration; the lighter four have night-layer twins): the five HIS layers, as small square swatches, legend keys, dots and bar fills. Only patient-admin and integration are dark enough for text; the rest are fills.
- **Model palette** (model-a0 to model-a5): the rules page's per-model series, with lighter dark-theme twins declared in that page's stylesheet.
- **On-fill** (on-fill; night-on-fill): text on any solid fill; white in light, near-black in dark, where the lighter hues cannot carry white.

### Neutral
- **Page** (page): the soft grey behind everything; also the plain buttons and the fake browser's address bar.
- **Card** (card): the white of every panel, the key-number strip, the segmented control, tiles, inputs and selects.
- **Recess** (recess): neutral badges, notes, code blocks, bar tracks, table layer rows, the fake browser chrome, a plain button's hover.
- **Line** (line): every rule and panel border.
- **Ink / Ink Soft / Ink Quiet** (ink, ink-soft, ink-quiet): headings and values / body, briefs and labels / footers, unselected step numbers, secondary metadata.
- **Terminal** (terminal, terminal-ink, terminal-ok, terminal-no, terminal-dim): a theme-invariant dark slab for command output and the gate log, identical in both themes.
- Dark theme: the night-* keys replace their light twins one for one; the page goes near-black and the panels one step lighter.

### Named Rules
**The Meaning or Place Rule.** A hue on the page must mean a technique, a layer, a model or a verdict, or mark the current place or choice in ours blue. Structure and emphasis are carried by ink, weight, rules and the grey-to-white step.

**The Fixed Identity Rule.** Ours is blue, AI agents are violet, the baseline is amber, on every page and in the deck. No chart, strip, lane or table may reassign these hues. Ours blue alone doubles as the accent for place, selection and the primary action.

**The Wash Rule.** A state is a tinted wash with text in its solid hue, not an outline: good-wash, bad-wash and warn-wash for verdicts, a 7–12% ours tint for a selection. Only a failure that matters goes solid.

**The 4.5 Floor Rule.** Small text holds at least 4.5:1 on its own background in both themes, including a verdict hue on its own wash (the washes are tuned to sit exactly there). Baseline amber and the lighter layer hues do not hold it and stay on fills and large figures.

## Typography

**Display Font:** Segoe UI Variable Display (with Segoe UI Variable Text, system-ui, -apple-system, Segoe UI, Roboto, sans-serif)
**Body Font:** Segoe UI Variable Text (with system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif)
**Label/Mono Font:** ui-monospace (with Cascadia Mono, Consolas, Courier New, monospace)

**Character:** Two optical cuts of one humanist family. The display cut, slightly tightened, carries the title, panel headings and every large number; the text cut carries the reading. Hierarchy comes from size, the display cut and 600 weight, never from capitals or letter-spacing. Mono appears only where the content is literally data.

### Hierarchy
- **Headline** (display, 600, 2rem, 1.15, -0.022em, balanced): the page title, once per page.
- **Title** (display, 600, 1.06rem, -0.005em): panel and section headings; index entries 1.12rem; module layers and fault titles 1.12rem; role names 1.1rem.
- **Subtitle** (text, 600, 0.9rem, ink-soft): sub-headings inside panels.
- **Key number** (display, 600, 1.8rem, 1.15, -0.02em, tabular): the key-number strip. Per-technique counts in the crawl lanes 2.3rem and in the patient columns 2.2rem; secondary figures (layer rows, day counter, stat numbers, index figures, module confidence) 1.35–1.6rem, all display 600 tabular.
- **Body** (text, 400, 1rem on a 15px root, 1.5): paragraphs capped at 78ch, step leads at 90ch; the page brief 1.02rem in ink-soft.
- **Label** (text, 400, 0.76–0.84rem, ink-soft or ink-quiet, sentence case): number captions (0.8rem), table headers (0.8rem, 600), legends, footers (0.78rem).
- **Data** (mono, 0.7–0.88rem, tabular): field names, URLs, codes, rule ids, paths, terminal text and right-aligned numeric cells.

### Named Rules
**The Offline Faces Rule.** No downloaded or web fonts: the pages open offline, so only faces the machine already has are named, each with a full fallback stack.

**The Display Is for Titles and Figures Rule.** The display cut sets the page title, panel headings and large numbers only; body, labels, buttons and tables stay in the text cut.

**The Sentence Case Rule.** No uppercase, letter-spaced labels and no eyebrow line above a heading; a label is a short sentence-case caption in ink-soft.

**The Mono Means Data Rule.** Monospace is for things a machine reads: field names, codes, URLs, paths, commands and numeric columns. Never for headings, briefs or decoration.

**The Tabular Numbers Rule.** Every number that can change or be compared uses tabular figures.

## Layout

A single centred column (max 1140px, padded 16px 20px 48px) on the grey page. The navigation links sit first; below them (18px) the header row puts the title and its one-line brief on the left and the tool buttons (A+, theme) on the right, closed by a 1px rule. Then the key-number strip, then the stepper whose panes hold the content, each 18px apart.

Inside panes, panels tile in fluid grids (`auto-fit`, 300px minimum) at a 16px gap; paired views use a 5:7 or 7:5 split that collapses to one column at 860–900px; the three technique lanes collapse at 980px; role, index and command rows collapse at 760px; the rules page's task grid stacks at 520px. Gaps step 4 / 8 / 12 / 16px; panels pad 16px 18px. Wide tables sit in a horizontal scroller. The root font size is the only density knob: 15px normally, 18px under A+, everything in rem.

The index is a plain list on the grey page: each demo is one ruled row of a coloured dot and name, a key number in the demo's colour with its caption, one line and an arrow (the portal row in ours blue, the dataset in green, the assistant in violet, the rules page in amber). Below it, a white panel of terminal commands (a label column and a mono command column).

### Named Rules
**The One-Line Brief Rule.** A page carries a title, a one-line brief, and a short lead per step. The presenter explains; the page never grows paragraphs of explanation, and every number stays labelled so an offline reader can still read it.

## Elevation & Depth

Flat, with one tonal step. There are no shadows anywhere and no gradients. Depth is the step from the grey page up to a white panel, held by a 1px line border; inside a panel, rules separate rows and cells and the recess grey sinks notes, tracks and code. The one layered element is the rules page's hover tooltip, an ink box with page-colour text and no shadow.

### Named Rules
**The Ruled, Not Lifted Rule.** A panel is separated by its white-on-grey step and its 1px rule, never by a shadow, a glow or a hover lift. Tints mark state, never structure.

## Shapes

Corners are small and consistent: 6px on panels, controls, fields, notes, verdict bars and terminals; 4px on chips, badges, field names, rule ids, bar tracks, matrix cells, the gate switch and the address bar; 2px on thin progress and life tracks, legend keys, swatches and inline highlights; 3px on kbd keys. Round shapes are reserved for markers that are dots by meaning: technique and demo dots, the rules page's model swatches and field dots, the fake browser's window dots, search squares in the crawl map, and the assistant's check marks. Borders are 1px line throughout; a dashed border marks "missed", "only in detail pages", "not this file" or "differs".

## Components

### Buttons
- **Shape:** 6px corners, 1px border.
- **Primary (Play, Send):** solid ours blue with on-fill text at 600, 5px 12px; hover mixes 15% ink into the blue; 55% opacity when disabled (50% for Send).
- **Plain:** page-grey with a line border and ink text at 600 (Start over, Watch a demo); hover takes the recess fill. The assistant's option buttons are the same on card, hover darkening the border to ink-quiet.
- **Tool buttons (A+, theme):** 2rem-high white bordered boxes in ink-soft; hover darkens text to ink and border to ink-quiet; pressed takes an ink border and ink text.
- **Focus:** a 2px Ours Blue outline at 2px offset on every control.

### Segmented control
- **Style:** one white bordered 6px box with 1px dividers between text buttons (0.86rem, 4px 11px).
- **State:** the pressed segment takes an 11% ours tint over the card, ink text and 600 weight.

### Selectable tiles
- **Style:** white bordered boxes (files, patients, roles) with a mono name or a display role name and a small ink-quiet caption.
- **State:** hover darkens the border to ink-quiet; pressed takes an ours border and a 7% ours tint; unavailable is ink-quiet text with a dashed border on no fill.

### Chips and badges
- **Style:** 4px, no border, 600 weight, 0.7–0.8rem; neutral badges sit on recess in ink-soft; field-name and rule chips are mono.
- **State:** verdict, category, rule and field states are the matching wash with text in the solid hue; a failure that matters is a solid red fill with on-fill text; a missing item is dashed, a blank one struck through; the current breadcrumb is a 14% ours tint in ours text. The assistant's cited rule is the one outlined chip, red on the page.

### Cards / Containers
- **Corner Style:** 6px.
- **Background:** card white on the grey page; recess for notes and code blocks.
- **Shadow Strategy:** none (see Elevation & Depth).
- **Border:** 1px line.
- **Internal Padding:** 16px 18px; a panel heading sits 10px above its content.

### Verdicts
A full-width 6px bar at 600: held or allowed on the green wash in green, declined or refused on the red wash in red, no border. The assistant's check marks are 1.6rem circles on the same washes.

### Inputs / Fields
- **Style:** 1px line border, 6px, card background, ink text (the assistant's input, selects).
- **Focus:** the global 2px Ours Blue outline; in the portal's sign-in replay the active field takes an Ours Blue border.
- **Disabled:** 50% opacity.

### Navigation
- **Style:** a row of plain text links (0.86rem, ink-soft, 20px apart). Hover darkens to ink; the current page is ink at 600 with a 2px Ours Blue underline. Scrolls horizontally without a scrollbar on narrow screens.

### Stepper (signature)
Underlined text tabs over a 1px rule: each tab is its label with a small tabular step number (0.8rem, ink-quiet) before it. The selected tab is ink at 600 with a 2px Ours Blue underline, and its number turns Ours Blue. Driven by `Kit.steps` with tab semantics: number keys and arrows move between panes, the hash records the step. Panes switch instantly.

### Key-number strip (signature)
One white bordered 6px panel split into equal cells (`auto-fit`, 130px minimum) by 1px dividers. Each cell is a 1.8rem display number over a 0.8rem ink-soft caption; the number takes its owner's hue (technique or verdict) or stays ink.

### Bars and tracks
A 12px recess track with 4px corners and a flat fill in the owner's hue, in a three-column row of label, track and value. Thinner 3–6px tracks at 2px corners carry progress, confidence and retention life.

### Heat maps
The rules page's per-rule table sets each value in a chip of ours blue mixed into the card by the score (6% at 0 to 50% at 1), ink text, so it reads in both themes. The dataset page's rule table mixes green into the red wash by the score.

### Tables
Collapsed, full-width, 0.86–0.88rem tabular; 1px line under each row, none under the last; headers 0.8rem 600 ink-soft; numeric cells right-aligned in mono.

### Terminal slab
A theme-invariant dark block (terminal, terminal-ink) in mono at 0.78–0.82rem, 6px corners, with terminal-ok, terminal-no and terminal-dim for pass, fail and quiet lines.

### Icons
One drawn stroke family in `Kit.icon`: 24-unit grid, 2 stroke, round caps and joins, `currentColor`, sized 1em. Check, x, play, pause, replay, lock, grid, ban, file, alert, stop, shield, theme, arrow, flag.

### Motion
Nothing animates on its own except the demos: the portal's sign-in replay and crawl playback, the dataset page's retention playback, the assistant's scripted scenes, and the login caret (a 1s stepped blink). Numbers are written in place (`Kit.count` returns plain text; `Kit.countIn` does nothing), panes appear without an entrance, controls have no hover lift, and the assistant's replies appear at once. Reduced motion switches every CSS animation and transition off; the portal then completes its sign-in replay at once and waits for Play before the crawl.

## Do's and Don'ts

### Do:
- **Do** colour a technique by its fixed hue (ours blue, agents violet, baseline amber) through a dot before its name and its numbers.
- **Do** set white panels on the grey page with a 1px line border at 6px corners, and chips at 4px.
- **Do** put a page's key numbers in one ruled strip, 1.8rem display at 600, each with a caption.
- **Do** mark the current nav link and the selected step with a 2px ours-blue underline, and a selection with a light ours tint.
- **Do** show verdict, category, rule and field states as a wash with text in the solid hue; go solid red only for a failure that matters.
- **Do** keep the display cut for the title, panel headings and large numbers, the text cut for everything else, and monospace for data.
- **Do** check every small text colour at 4.5:1 or better on its own background in both themes, and use on-fill for text on solid fills.
- **Do** read every number from a committed artefact and give it a label.
- **Do** draw icons from `Kit.icon` and give every control a visible 2px Ours Blue focus outline and a keyboard path.

### Don't:
- **Don't** add shadows, gradients, glows or hover lifts.
- **Don't** use pill shapes or full rounding on controls, chips or tracks.
- **Don't** outline a state where a wash will do, or fill a button other than the demo's primary action.
- **Don't** animate numbers, panes or replies; only the demos move.
- **Don't** use colour for structure or decoration; it is reserved for data meaning and the current place.
- **Don't** use uppercase letter-spaced labels or an eyebrow or kicker line.
- **Don't** load web fonts, CDNs or any external asset; the pages open offline.
- **Don't** add explanatory paragraphs; one-line briefs only, the presenter explains.
- **Don't** use emoji or unicode glyphs as icons.
- **Don't** reassign the three technique hues inside a chart, strip, lane or table.
