/* The HIS Staff Assistant portal: the enquiry desk on the left, the request's route on the right.
   A request walks five stops on one track, each lit by what the engine decided: understood, the staff-only door
   (the DPDP check for this badge, before any detail is asked), the details, the department, and the
   screen, where a replica of the hospital's portal lights the column and the button the step uses.
   Keys: / to type, 1 2 3 a badge, T a tour, Space lands what is moving (in a tour: its next turn), Esc to stop it. */
(() => {
  "use strict";
  const { D, F, R } = Engine;
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const cap = (s) => String(s).charAt(0).toUpperCase() + String(s).slice(1);
  const dash = (s) => String(s).replace(/ -- /g, " — ").replace(/--/g, "—");
  const human = (s) => String(s).replace(/_/g, " ");
  const ids = (h) => String(h).replace(/\b(?:MRN\d+|[A-Z]{2,}-\d[\d-]*\d)\b/g, (m) => `<span class="id">${m}</span>`);
  const slotLabel = (n) => cap(String(n).replace(/\bmrn\b/g, "MRN").replace(/_id\b/g, " ID").replace(/_/g, " "));
  const fmt = (n) => Number(n).toLocaleString("en-IN");
  const still = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
  const icon = (id) => `<svg viewBox="0 0 24 24" aria-hidden="true"><use href="#${id}"/></svg>`;
  const SCREENS = Object.fromEntries(D.screens.map((s) => [s.title, s]));
  const LAYER_OF = Object.fromEntries(D.screens.map((s) => [s.title, s.layer]));
  const dept = (layer) => `--dc: var(--d-${layer})`;
  const PHONE = matchMedia("(max-width: 860px)"), NARROW = matchMedia("(max-width: 520px)");

  /* ------------------------------------------------------------ state */
  let role = "reception", session = new Engine.Session(role), history = [], ctx = null, epoch = 0;
  let board = null, stepAt = 0;
  const STAGES = [
    { id: "enquiry", name: "Enquiry", icon: "p-desk" },
    { id: "door", name: "Staff only", icon: "p-door" },
    { id: "details", name: "Details", icon: "p-form" },
    { id: "dept", name: "Department", icon: "p-signpost" },
    { id: "screen", name: "Screen", icon: "p-screen" },
  ];
  const mine = (r) => D.functions.filter((f) => R[r].gate[f.id].allowed);

  /* ------------------------------------------------------------ motion: short, and it lands */
  const timers = new Map();          // timer id -> what it will do, so a new turn can land it now
  const later = (ms, fn) => { if (still() || ms <= 0) { fn(); return; } const t = setTimeout(() => { timers.delete(t); fn(); }, ms); timers.set(t, fn); };
  function land() {
    for (const [t, fn] of [...timers]) { clearTimeout(t); timers.delete(t); fn(); }
    document.getAnimations().forEach((a) => { try { if (a.effect && a.effect.getComputedTiming().endTime !== Infinity) a.finish(); } catch (e) { /* left to run */ } });
  }
  const anim = (el, frames, o) => (el && !still() ? el.animate(frames, { duration: 220, easing: "cubic-bezier(.16, 1, .3, 1)", fill: "backwards", ...o }) : null);
  const rise = (el, delay = 0) => anim(el, [{ opacity: 0, transform: "translateY(4px)" }, { opacity: 1, transform: "none" }], { delay });

  /* ------------------------------------------------------------ the engine, live or replayed */
  function replay(turns) {
    const v = D.vectors.concat(D.tours).find((c) => c.role === role && turns.length <= c.turns.length && turns.every((t, i) => c.turns[i] === t));
    return v ? v.replies[turns.length - 1] : { kind: "unrecognised", fn: null, text: "(Typing is off on this copy: choose a task or play the tour.)" };
  }
  function respond(text, recorded) {
    history.push(text);
    if (!Engine.live) return recorded || replay(history);
    return session.respond(text);
  }

  /* ------------------------------------------------------------ the request's route, from what the engine decided */
  function track(text, r, wasIdle) {
    if (wasIdle || r.kind === "unrecognised" || r.kind === "help" || r.kind === "changes" || !ctx) ctx = { request: text, fn: null, reply: r };
    ctx.reply = r;
    if (r.fn) ctx.fn = r.fn;
    if (r.kind === "ask_choose") ctx.options = r.text.split("\n").filter((l) => /^\s+\d+\./.test(l)).map((l) => l.replace(/^\s+\d+\.\s*/, ""));
    if (r.kind === "ask_input" && Engine.live) ctx.slots = { inputs: { ...session.inputs }, prefilled: [...session.prefilled], misfits: { ...session.misfits }, pending: session.pending() && session.pending().name };
    if (r.kind === "guidance" && Engine.live && session.last) ctx.slots = { inputs: session.last.inputs, prefilled: session.last.prefilled, misfits: session.last.misfits, pending: null };
    if (r.kind === "guidance") stepAt = 0;
  }
  function states() {
    if (!ctx) return ["waiting", "waiting", "waiting", "waiting", "waiting"];
    const k = ctx.reply.kind;
    if (k === "unrecognised") return ["unknown", "waiting", "waiting", "waiting", "waiting"];
    if (k === "ask_choose") return ["current", "waiting", "waiting", "waiting", "waiting"];
    if (k === "declined") return ["passed", "stopped", "waiting", "waiting", "waiting"];
    if (k === "ask_input") return ["passed", "passed", "current", "waiting", "waiting"];
    if (k === "guidance") return ["passed", "passed", "passed", "passed", "passed"];
    return ["waiting", "waiting", "waiting", "waiting", "waiting"];
  }
  function modulesOf(fn) {
    const seen = [];
    for (const s of F[fn].steps) { const m = s.place && s.place.module; if (m && !seen.includes(m)) seen.push(m); }
    return seen;
  }
  function statusLine(i, st) {
    const f = ctx && ctx.fn ? F[ctx.fn] : null, k = ctx ? ctx.reply.kind : null;
    if (i === 0) return !ctx ? "Ask at the desk" : k === "unrecognised" ? "Not an HIS task" : k === "ask_choose" ? `Which one of ${ctx.options.length}?` : f ? "Understood" : "Waiting";
    if (i === 1) {
      if (st === "stopped") return `No entry · ${String(R[role].gate[ctx.fn].rule).replace("-", "‑")}`;
      return st === "passed" ? "Open: 3 of 3 rules" : "Waiting";
    }
    if (i === 2) {
      if (!f || st === "waiting") return "Waiting";
      const n = f.inputs.length;
      if (!n) return "None needed";
      if (st === "passed") return `All ${n} given`;
      const got = ctx.slots ? Object.keys(ctx.slots.inputs).length : 0;
      return `${got} of ${n} given`;
    }
    if (i === 3) { if (st !== "passed") return "Waiting"; const ms = modulesOf(ctx.fn); return ms.length ? ms[0] + (ms.length > 1 ? ` +${ms.length - 1}` : "") : "Not placed"; }
    if (st !== "passed") return "Waiting";
    return `${f.steps.length} ${f.steps.length === 1 ? "step" : "steps"} placed`;
  }
  function paintStages(animate) {
    const want = states(), lis = [...$("stages").children];
    // Signs hold their places; only their state changes, one after another as the engine decided.
    let d = 0;
    want.forEach((st, i) => {
      const sign = lis[i].querySelector(".sign"), changed = sign.dataset.state !== st;
      const apply = () => {
        sign.dataset.state = st;
        lis[i].classList.toggle("lit", st === "passed");
        const tile = sign.querySelector(".tile");
        const layer = i === 3 && st === "passed" ? (modulesOf(ctx.fn)[0] ? LAYER_OF[modulesOf(ctx.fn)[0]] : null) : null;
        tile.classList.toggle("dept", !!layer);
        tile.style.cssText = layer ? dept(layer) : "";
        tile.innerHTML = icon(layer ? `d-${layer}` : st === "passed" ? "p-check" : st === "stopped" ? "p-noentry" : st === "unknown" ? "p-question" : STAGES[i].icon);
        sign.querySelector(".sl > span").textContent = statusLine(i, st);
        sign.setAttribute("aria-label", `${STAGES[i].name}: ${statusLine(i, st)}`);
        if (changed && animate) anim(tile, [{ transform: "scale(.82)" }, { transform: "none" }], { duration: 240 });
        if (changed && animate && st === "passed" && lis[i + 1] && !still()) {
          lis[i + 1].animate([{ clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0 0 0)" }], { duration: 180, easing: "cubic-bezier(.16, 1, .3, 1)", pseudoElement: "::before", fill: "backwards" });
        }
      };
      if (animate && changed && st !== "waiting") { later(d, apply); d += 190; } else apply();
    });
    return d;
  }
  // The bar's status pill: what the route is doing, then where the request ended.
  function setStatus(cls, text) { const s = $("status"); s.className = `status ${cls}`; s.querySelector("span").textContent = text; }
  function settled() {
    const k = ctx ? ctx.reply.kind : null;
    if (k === "guidance") { const n = F[ctx.fn].steps.length; return setStatus("done", `${n} ${n === 1 ? "step" : "steps"} placed`); }
    if (k === "declined") return setStatus("stop", `Refused · ${String(R[role].gate[ctx.fn].rule).replace("-", "‑")}`);
    if (k === "ask_input") return setStatus("at", "Asking for a detail");
    if (k === "ask_choose") return setStatus("at", "Which task?");
    if (k === "unrecognised") return setStatus("ready", "Not an HIS task");
    return setStatus("ready", "Ready");
  }

  function furthest() {
    const st = states();
    if (!ctx) return 0;
    if (st[1] === "stopped") return 1;
    if (st[4] === "passed") return 4;
    if (st[2] === "current") return 2;
    return 0;
  }

  /* ------------------------------------------------------------ the boards */
  function boardEnquiry() {
    if (!ctx) return `<h2>Enquiry</h2><p class="lede">Ask at the desk. The route lights as the assistant decides, and the screen shows where each step happens.</p>`;
    const k = ctx.reply.kind;
    let said = esc(ctx.request);
    if (ctx.fn) {
      const m = Engine.matched(ctx.request, ctx.fn);
      for (const w of m.words) said = said.replace(new RegExp(`\\b(${w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})\\b`, "i"), "<mark>$1</mark>");
    }
    if (k === "unrecognised") return `<h2>Enquiry</h2><p class="said">“${said}”</p><p class="lede">Not one of the hospital system's tasks, so nothing further happens: no door, no details.</p>`;
    if (k === "ask_choose") return `<h2>Enquiry <span class="muted">· sounds like ${ctx.options.length} tasks, so it asks rather than guesses</span></h2><p class="said">“${said}”</p><div class="choices">${ctx.options.map((o, i) => `<span class="chip"><b>${i + 1}</b> ${esc(cap(o))}</span>`).join("")}</div>`;
    const f = F[ctx.fn];
    return `<h2>Enquiry</h2><p class="said">“${said}”</p><p class="lede">Understood as <b>${esc(f.label)}</b> <span class="muted">· ${esc(f.group)}</span></p>`;
  }
  function boardDoor() {
    if (!ctx || !ctx.fn) return `<h2>Staff only</h2><p class="lede">Every task is checked against your badge before a single detail is asked.</p>`;
    const g = R[role].gate[ctx.fn];
    let stopped = false;
    const rules = g.checks.map((c) => {
      const s = stopped ? "skip" : c.ok ? "ok" : "no";
      if (!c.ok) stopped = true;
      return `<li class="${s}"><span class="tile ${s === "ok" ? "go" : s === "no" ? "stop" : "skip"}">${icon(s === "ok" ? "p-check" : s === "no" ? "p-noentry" : "p-door")}</span><span class="rid">${esc(c.rule)}</span><span><span class="rn">${esc(cap(c.name))}</span><span class="rd">${esc(human(c.detail))}${s === "skip" ? " · not reached" : ""}</span></span></li>`;
    }).join("");
    return `<h2>Staff only <span class="muted">· ${esc(cap(role))} badge</span></h2><ul class="rules">${rules}</ul>`;
  }
  function boardDetails() {
    if (!ctx || !ctx.fn || ctx.reply.kind === "declined") return `<h2>Details</h2><p class="lede">Only the details the task needs, each checked for its shape.</p>`;
    const f = F[ctx.fn], sl = ctx.slots || { inputs: {}, prefilled: [], misfits: {}, pending: null };
    if (!f.inputs.length) return `<h2>Details</h2><p class="lede">This task needs no details.</p>`;
    const rows = f.inputs.map((s) => {
      const v = sl.inputs[s.name], pend = sl.pending === s.name;
      const how = v != null ? (sl.prefilled.includes(s.name) ? "taken from your message" : sl.misfits[s.name] ? "given after one that did not fit" : "given") : pend ? (sl.misfits[s.name] ? "did not fit; asked again" : "asked now") : "not yet";
      return `<li><span class="tile ${v != null ? "go" : "wait"}">${icon(v != null ? "p-check" : "p-form")}</span><span><span class="sn">${esc(slotLabel(s.name))}</span><span class="sv">${v != null ? ids(esc(v)) + " · " : ""}${how}</span></span></li>`;
    }).join("");
    return `<h2>Details <span class="muted">· ${esc(f.label)}</span></h2><ul class="slots">${rows}</ul>`;
  }
  function boardDept() {
    if (!ctx || !ctx.fn || states()[3] !== "passed") return `<h2>Department</h2><p class="lede">The hospital system's five modules; the route goes to the ones the steps need.</p>`;
    const f = F[ctx.fn], used = {};
    f.steps.forEach((s, i) => { if (s.place) (used[s.place.module] = used[s.place.module] || []).push(i + 1); });
    const p = D.purposes[f.purpose];
    return `<h2>Department</h2><ul class="dirs">${D.screens.map((s) => `<li class="${used[s.title] ? "on" : "off"}" style="${dept(s.layer)}"><span class="tile dept">${icon(`d-${s.layer}`)}</span><span class="dn">${esc(s.title)}</span><span class="ds">${used[s.title] ? `Step ${used[s.title].join(", ")}` : ""}</span></li>`).join("")}</ul>
      <p class="facts"><span><b>Purpose</b> ${esc(human(f.purpose))}</span><span><b>Data</b> ${esc(human(f.touched))}</span><span><b>Keep</b> up to ${fmt(p.days)} days</span></p>`;
  }
  function boardScreen() {
    if (!ctx || !ctx.fn || states()[4] !== "passed") return `<h2>Screen</h2><p class="lede">Each step is placed on the screen where it happens, worded with the portal's own labels and buttons.</p>`;
    const f = F[ctx.fn], s = f.steps[stepAt], pl = s.place, layer = pl ? LAYER_OF[pl.module] : s.layer;
    const sel = `<div class="stepsel" role="group" aria-label="Step shown on the screen">${f.steps.map((st, i) => {
      const l = st.place ? LAYER_OF[st.place.module] : st.layer;
      return `<button type="button" data-step="${i}" aria-pressed="${i === stepAt}" style="${dept(l)}">${i + 1}</button>`;
    }).join("")}</div>`;
    const lit = pl ? s.fields.map((x) => pl.labels[x]).filter(Boolean) : [];
    const rows = pl && pl.screen === "record page";
    const spot = pl ? `<dl class="spot" style="${dept(layer)}">
        <div><dt>Module</dt><dd class="mod">${esc(pl.module)}</dd></div>
        <div><dt>Page</dt><dd>${esc(cap(pl.screen))}</dd></div>
        <div><dt>${rows ? "Rows" : "Columns"} lit</dt><dd>${lit.length ? lit.map(esc).join(" · ") : `<span class="nil">–</span>`}</dd></div>
        <div><dt>Press</dt><dd>${pl.button ? `<span class="btn">${esc(pl.button)}</span>` : `<span class="nil">–</span>`}</dd></div></dl>`
      : `<p class="lede">Not placed on a screen of the hospital system, so it is withheld rather than guessed.</p>`;
    return `<div class="bh"><h2>Screen <span class="muted">· step ${stepAt + 1} of ${f.steps.length}</span></h2>${sel}</div>${spot}<p class="now">${ids(esc(dash(stepText(ctx.reply, stepAt))))}</p>`;
  }
  const BOARDS = [boardEnquiry, boardDoor, boardDetails, boardDept, boardScreen];
  function paintBoard(i, animate) {
    board = i;
    [...$("stages").children].forEach((li, k) => li.querySelector(".sign").setAttribute("aria-current", String(k === i)));
    $("board").innerHTML = BOARDS[i]();
    $("board").querySelectorAll("[data-step]").forEach((b) => b.addEventListener("click", () => showStep(+b.dataset.step)));
    if (animate) anim($("board"), [{ opacity: .45 }, { opacity: 1 }], { duration: 220 });
  }

  /* ------------------------------------------------------------ the replica: the hospital's portal, as crawled */
  function stepText(r, i) {
    const lines = r.text.split("\n"), out = [];
    for (const l of lines) { const m = l.match(/^  (\d+)\. (.*)$/); if (m) out.push(m[2]); }
    return out[i] || "";
  }
  function paintScreen(animate) {
    const el = $("screen");
    const chrome = `<div class="chrome"><b>HIS Portal</b><span class="who">signed in: ${esc(role)}</span></div>`;
    if (!ctx || !ctx.fn || states()[4] !== "passed") {
      el.style.cssText = "";
      el.innerHTML = chrome + `<div class="tabs">${D.screens.map((s) => `<span>${esc(s.title)}</span>`).join("")}</div>`
        + `<div class="page"><div class="ph"><b>Home</b><span>The hospital system's modules</span></div><table class="modlist"><thead><tr><th>Module</th><th>Buttons</th><th>Fields</th></tr></thead><tbody>${D.screens.map((s) => `<tr><td><span class="mi">${icon(`d-${s.layer}`)}</span>${esc(s.title)}</td><td>${s.listButtons.length + s.recordButtons.length}</td><td>${s.record.length}</td></tr>`).join("")}</tbody></table></div>`;
      return;
    }
    const f = F[ctx.fn], step = f.steps[stepAt], place = step.place;
    if (!place) {
      el.innerHTML = chrome + `<div class="page"><div class="withheld">This step could not be placed on a screen of the hospital system, so it is withheld rather than guessed.</div></div>`;
      return;
    }
    const scr = SCREENS[place.module], layer = scr.layer, uses = new Set(step.fields);
    el.style.cssText = dept(layer);
    const record = place.screen === "record page";
    const buttons = record ? scr.recordButtons : scr.listButtons;
    const tools = buttons.length ? `<div class="tools">${buttons.map((b) => `<span class="${b === place.button ? "press" : ""}">${esc(b)}</span>`).join("")}</div>` : "";
    let body;
    if (record) {
      body = `<div class="rec">${scr.record.map((c) => `<div class="k ${uses.has(c.field) ? "use" : ""}">${esc(c.label)}</div><div class="v ${uses.has(c.field) ? "use" : ""}"></div>`).join("")}</div>`;
    } else {
      body = `<table><thead><tr>${scr.list.map((c) => `<th class="${uses.has(c.field) ? "use" : ""}">${esc(c.label)}</th>`).join("")}</tr></thead><tbody>${[0, 1, 2, 3].map(() => `<tr>${scr.list.map((c) => `<td class="${uses.has(c.field) ? "use" : ""}"></td>`).join("")}</tr>`).join("")}</tbody></table>`;
    }
    el.innerHTML = chrome + `<div class="tabs">${D.screens.map((s) => `<span class="${s.title === place.module ? "on" : ""}">${esc(s.title)}</span>`).join("")}</div>`
      + `<div class="page"><div class="ph"><b>${esc(place.module)}</b><span>${esc(place.screen)}</span></div>${tools}${body}<p class="nodata">No patient data is shown here.</p></div>`;
    // the "you are here" pin, on the page's title line: what this step does on this screen
    const target = el.querySelector(".tools .press");
    const pin = document.createElement("span");
    pin.className = "pin"; pin.setAttribute("aria-hidden", "true");
    const lit = record ? (uses.size === 1 ? "row" : "rows") : (uses.size === 1 ? "column" : "columns");
    pin.innerHTML = `${icon("p-pin")}<span>Step ${stepAt + 1}: ${target ? `press ${esc(place.button)}` : uses.size ? `use the lit ${lit}` : "on this screen"}</span>`;
    el.querySelector(".ph").append(pin);
    const on = el.querySelector(".tabs .on");
    if (on && on.parentElement.scrollWidth > on.parentElement.clientWidth) on.parentElement.scrollLeft = Math.max(0, on.offsetLeft - 12);
    if (animate) {
      anim(el.querySelector(".page"), [{ opacity: .35 }, { opacity: 1 }], { duration: 220 });
      anim(pin, [{ opacity: 0, transform: "translateX(6px)" }, { opacity: 1, transform: "none" }], { duration: 240, delay: 140 });
      if (target) anim(target, [{ boxShadow: "0 0 0 0 transparent" }, { boxShadow: "0 0 0 3px color-mix(in srgb, var(--dc) 22%, transparent)" }], { duration: 280, delay: 200, easing: "ease-out" });
    }
  }
  function showStep(i) {
    stepAt = i;
    $("log").querySelectorAll(".step").forEach((b) => b.setAttribute("aria-pressed", String(b.closest(".msg") === lastGuidance && +b.dataset.step === i)));
    paintBoard(4, false);
    paintScreen(true);
  }

  /* ------------------------------------------------------------ the desk: replies as signs */
  let lastGuidance = null;
  function guidanceHTML(r) {
    const f = F[r.fn], lines = r.text.split("\n"), p = D.purposes[f.purpose];
    const steps = [];
    let n = -1;
    for (const l of lines) {
      const m = l.match(/^  (\d+)\. (.*)$/);
      if (m) { n++; steps.push({ text: m[2], note: null }); continue; }
      const c = l.match(/^\s+note: (.*)$/);
      if (c && n >= 0) steps[n].note = c[1];
    }
    const withheld = lines[2] === D.texts.withheldHead;
    return `<h3>${esc(cap(f.label))}</h3>`
      + (withheld ? `<p class="soft">${esc(dash(D.texts.withheldHead.trim()))}</p>` : "")
      + `<ol class="steps">${steps.map((s, i) => {
        const st = f.steps[i] || {}, pl = st.place, layer = pl ? LAYER_OF[pl.module] : st.layer;
        const where = pl ? `<span class="where"><b>${esc(pl.module)}</b><span>${esc(pl.screen)}</span>${pl.button ? `<span class="btn">${esc(pl.button)}</span>` : ""}</span>` : `<span class="where"><span>${esc(st.where || "not placed")}</span></span>`;
        return `<li><button class="step" type="button" data-step="${i}" aria-pressed="${i === 0}" style="${dept(layer)}"><span class="num">${i + 1}</span><span><span class="tx">${ids(esc(dash(s.text)))}</span>${where}${s.note ? `<span class="note">${esc(dash(s.note))}</span>` : ""}</span></button></li>`;
      }).join("")}</ol>`
      + `<p class="facts"><span><b>Why</b> part of your work as ${esc(role)}: ${esc(p.plain || "")}</span><span><b>Keep</b> no longer than ${fmt(p.days)} days</span></p>`;
  }
  function declinedHTML(r) {
    const lines = r.text.split("\n"), f = F[r.fn];
    const ruleAt = lines.findIndex((l) => /^\s+\[/.test(l));
    const after = lines.slice(ruleAt + 1).map((l) => l.trim()).filter(Boolean);
    return `<div class="refusal"><h3>Not for ${esc(cap(role))}: ${esc(f.label)}</h3><p>${esc(dash(lines[0]))}</p>`
      + after.map((l) => `<p class="who">${icon("p-arrow")}<span>${esc(dash(l))}</span></p>`).join("")
      + `<p class="asked-none">No patient details were asked for.</p></div>`;
  }
  function listHTML(r) {
    const lines = r.text.split("\n");
    let h = "", opts = [];
    const flush = () => { if (opts.length) { h += `<div class="choices">${opts.join("")}</div>`; opts = []; } };
    for (const l of lines) {
      const m = l.match(/^\s+(?:(\d+)\.|-) (.*)$/);
      if (m) { opts.push(`<button class="chip say" type="button" data-say="${esc(m[1] || m[2])}">${esc(cap(m[2]))}</button>`); continue; }
      flush();
      const g = l.match(/^\s+(.*):$/);
      if (g) h += `<p class="grp">${esc(g[1])}</p>`;
      else if (l.trim()) h += `<p class="${/^Say "cancel"/.test(l) ? "soft" : ""}">${esc(dash(l))}</p>`;
    }
    flush();
    return h;
  }
  function askHTML(r) {
    const lines = r.text.split("\n"), last = lines.pop(), ex = last.match(/^(.*) \(e\.g\. (.*)\)$/);
    const pre = lines.map((l) => (l === D.texts.misfit ? `<p class="misfit">${esc(l)}</p>` : `<p class="soft">${ids(esc(dash(l)))}</p>`)).join("");
    const f = r.fn ? F[r.fn] : null, prog = f && Engine.live && session.state === "collecting" ? `Detail ${Object.keys(session.inputs).length + 1} of ${f.inputs.length}` : "";
    return pre + `<div class="question"><p class="q">${esc(ex ? ex[1] : last)}</p><div class="qrow">${prog ? `<span class="prog">${prog}</span>` : ""}${ex ? `<button class="chip say" type="button" data-say="${esc(ex[2])}">Use the example: <b>${ids(esc(ex[2]))}</b></button>` : ""}</div></div>`;
  }
  function replyHTML(r) {
    if (r.kind === "guidance") return guidanceHTML(r);
    if (r.kind === "declined") return declinedHTML(r);
    if (r.kind === "ask_choose" || r.kind === "unrecognised" || r.kind === "help") return listHTML(r);
    if (r.kind === "ask_input") return askHTML(r);
    if (r.kind === "changes") {
      const lines = r.text.split("\n"), items = lines.slice(1).filter((l) => l.trim());
      return `<p>${esc(dash(lines[0]))}</p>${items.length ? `<ul class="steps">${items.map((l) => `<li class="soft">${esc(dash(l.replace(/^\s+- /, "").trim()))}</li>`).join("")}</ul>` : ""}`;
    }
    if (r.kind === "cancelled") return `<p>${esc(dash(r.text))}</p><span class="stamp-line">Stopped</span>`;
    return `<p>${esc(dash(r.text))}</p>`;
  }
  function tileFor(r) {
    if (r.kind === "declined") return `<span class="tile stop">${icon("p-noentry")}</span>`;
    if (r.kind === "guidance") return `<span class="tile go">${icon("p-check")}</span>`;
    if (r.kind === "unrecognised") return `<span class="tile">${icon("p-question")}</span>`;
    return `<span class="tile">${icon("p-info")}</span>`;
  }
  function add(kind, html, tile = "") {
    const div = document.createElement("div");
    div.className = `msg ${kind}`;
    div.innerHTML = kind === "you" ? `<span class="sr-only">You:</span><span class="slip">${html}</span>` : `${tile}<div class="body"><span class="sr-only">Assistant:</span>${html}</div>`;
    $("log").append(div);
    div.querySelectorAll(".say").forEach((b) => b.addEventListener("click", () => ask(b.dataset.say)));
    div.querySelectorAll(".step").forEach((b) => b.addEventListener("click", () => { if (div === lastGuidance) showStep(+b.dataset.step); }));
    const log = $("log");
    if (log.scrollHeight > log.clientHeight + 1) log.scrollTop = kind === "bot" && div.offsetHeight > log.clientHeight * 0.6 ? div.offsetTop - 12 : log.scrollHeight;
    else if (kind === "bot" && PHONE.matches && log.childElementCount > 1) div.scrollIntoView({ block: "start", behavior: still() ? "auto" : "smooth" });
    rise(div);
    return div;
  }

  /* ------------------------------------------------------------ a turn: the desk answers, the route walks */
  // A tour passes its recorded reply: a tour holds more than one request, which a replay by prefix cannot follow.
  function ask(text, fromTour = false, recorded = null) {
    if (touring && !fromTour) return;
    land();
    const wasIdle = !Engine.live ? history.length === 0 || ["guidance", "declined", "unrecognised", "help", "changes", "cancelled"].includes(ctx && ctx.reply.kind) : session.state === "idle";
    if (!Engine.live && wasIdle) history = [];
    add("you", ids(esc(text || "(nothing)")));
    const r = respond(text, recorded);
    if (["guidance", "declined", "unrecognised", "help", "changes", "cancelled"].includes(r.kind)) history = [];
    track(text, r, wasIdle);
    if (r.kind === "cancelled" || r.kind === "help" || r.kind === "changes") ctx = null;
    const div = add("bot", replyHTML(r), tileFor(r));
    if (r.kind === "guidance") { lastGuidance = div; }
    const d = paintStages(true);
    if (d > 0 && !still()) {
      [...$("stages").children].forEach((li) => li.querySelector(".sign").setAttribute("aria-current", "false"));
      $("board").classList.add("pending"); $("screen").classList.add("pending");
      setStatus("run", "Walking the route");
    }
    later(d, () => { $("board").classList.remove("pending"); $("screen").classList.remove("pending"); paintBoard(furthest(), true); paintScreen(true); settled(); });
  }

  /* ------------------------------------------------------------ badges, tasks, welcome */
  function paintBadges() {
    $("badges").innerHTML = D.roles.map((r, i) => `<button class="badge" type="button" data-role="${r.id}" aria-pressed="${r.id === role}" aria-keyshortcuts="${i + 1}" title="${mine(r.id).length} tasks"><b>${esc(cap(r.id))}</b></button>`).join("");
    $("badges").querySelectorAll(".badge").forEach((b) => b.addEventListener("click", () => setRole(b.dataset.role)));
  }
  // The welcome: two of the badge's common tasks and one it may not do, so the staff-only door is found.
  function welcome() {
    const common = (D.common[role] || []).filter((id) => F[id]).slice(0, 2), out = D.outside[role];
    const start = (id, cls = "", tag = "") => `<button class="start say ${cls}" type="button" data-say="${esc(F[id].label)}">${cls ? icon("p-noentry") : ""}<span class="st">${esc(cap(F[id].label))}</span>${tag ? `<small>${tag}</small>` : ""}${icon("p-chev")}</button>`;
    add("bot", `<p class="greet">What do you need to do in the hospital system?</p>
      <p class="soft">Ask in your own words, or start with one of these.</p>
      <div class="starts">${common.map((id) => start(id)).join("")}${out ? start(out, "out", `Not for ${esc(role)}`) : ""}</div>`, `<span class="tile">${icon("p-info")}</span>`);
  }
  function setRole(r) {
    if (touring) stopTour();
    land();
    epoch++;
    role = r; session = new Engine.Session(role); history = []; ctx = null; lastGuidance = null; stepAt = 0;
    document.body.dataset.role = r;
    $("log").innerHTML = "";
    paintBadges(); welcome();
    paintStages(false); paintBoard(0, false); paintScreen(false); settled();
  }

  /* ------------------------------------------------------------ the tour: one recorded conversation per badge */
  let touring = false, tourStep = 0, tourTimer = null, waitingNext = null;
  const sleep = (ms) => new Promise((res) => { if (still()) ms = Math.min(ms, 300); tourTimer = setTimeout(res, ms); waitingNext = res; });
  async function typeInto(text) {
    const box = $("input");
    box.value = "";
    for (const ch of text) { if (!touring) return; box.value += ch; await new Promise((res) => setTimeout(res, still() ? 0 : 26)); }
    await sleep(380);
    box.value = "";
  }
  async function playTour() {
    const tour = D.tours.find((t) => t.role === role);
    if (!tour) return;
    const my = ++epoch;
    setRole(role); epoch = my;
    touring = true; document.body.classList.add("touring");
    $("tour").setAttribute("aria-pressed", "true"); $("tour").querySelector("span").textContent = "Stop";
    $("input").disabled = true;
    for (tourStep = 0; tourStep < tour.turns.length; tourStep++) {
      if (!touring || my !== epoch) return;
      await typeInto(tour.turns[tourStep]);
      if (!touring || my !== epoch) return;
      ask(tour.turns[tourStep], true, tour.replies[tourStep]);
      const kind = tour.replies[tourStep].kind;
      await sleep(kind === "declined" ? 3200 : kind === "guidance" ? 1800 : 1500);
    }
    // the last answer stays; walk the steps on the screen
    const f = ctx && ctx.fn ? F[ctx.fn] : null;
    if (f) for (let i = 1; i < f.steps.length && touring && my === epoch; i++) { await sleep(1700); if (touring && my === epoch) showStep(i); }
    stopTour();
  }
  function stopTour() {
    touring = false; document.body.classList.remove("touring");
    clearTimeout(tourTimer);
    $("tour").setAttribute("aria-pressed", "false"); $("tour").querySelector("span").textContent = "Tour";
    $("input").disabled = !Engine.live;
    $("input").value = "";
  }
  function nextNow() { if (!touring) return; land(); clearTimeout(tourTimer); if (waitingNext) waitingNext(); }
  $("tour").addEventListener("click", () => (touring ? stopTour() : playTour()));
  $("alltasks").addEventListener("click", () => ask("help"));

  /* ------------------------------------------------------------ wiring */
  $("stages").innerHTML = STAGES.map((s, i) => `<li><button class="sign" type="button" data-board="${i}" data-state="waiting"><span class="tile">${icon(s.icon)}</span><span class="sl"><b>${esc(s.name)}</b><span>Waiting</span></span></button></li>`).join("");
  $("stages").querySelectorAll(".sign").forEach((b) => b.addEventListener("click", () => paintBoard(+b.dataset.board, true)));
  $("ask").addEventListener("submit", (e) => {
    e.preventDefault();
    if (touring || !Engine.live) return;
    const t = $("input").value.trim();
    if (!t) return;
    $("input").value = "";
    ask(t);
  });
  document.addEventListener("keydown", (e) => {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const typing = document.activeElement === $("input");
    if (e.key === "Escape" && touring) { stopTour(); e.preventDefault(); return; }
    if (typing) return;
    if (e.key === "/") { $("input").focus(); e.preventDefault(); }
    else if (/^[1-3]$/.test(e.key)) { setRole(D.roles[+e.key - 1].id); e.preventDefault(); }
    else if (e.key === "t" || e.key === "T") { touring ? stopTour() : playTour(); e.preventDefault(); }
    else if (e.key === " ") { if (touring) nextNow(); else land(); e.preventDefault(); }
  });

  $("foot").innerHTML = (Engine.live
    ? `<span class="ok"><i aria-hidden="true"></i>Rule-based, no AI model · checked against ${fmt(Engine.checked)} recorded conversations</span>`
    : `<span class="off">Rule-based, no AI model · typing is off on this copy; the tours and tasks still play</span>`)
    + `<span class="keys"><kbd>/</kbd> ask <kbd>T</kbd> tour <kbd>Space</kbd> next</span>`;
  const placeholder = () => { $("input").placeholder = !Engine.live ? "Typing is off on this copy" : NARROW.matches ? "Ask for an HIS task" : "Ask for an HIS task, in your own words"; };
  NARROW.addEventListener("change", placeholder); placeholder();
  if (!Engine.live) $("input").disabled = true;

  setRole(role);
  if (!matchMedia("(max-width: 860px)").matches) $("input").focus({ preventScroll: true });
})();
