/* Shared by every demo page (inlined at build time): the header buttons, the
   stepper, and numbers that count up when their pane comes into view. */
window.Kit = (() => {
  const still = matchMedia("(prefers-reduced-motion: reduce)").matches;

  // <span data-count="440" data-dp="0" data-suffix="×">440</span> counts up from zero.
  function countIn(root) {
    (root || document).querySelectorAll("[data-count]").forEach((el) => {
      const to = Number(el.dataset.count), dp = Number(el.dataset.dp || 0), suf = el.dataset.suffix || "";
      const fmt = (v) => (dp ? v.toFixed(dp) : Math.round(v).toLocaleString("en-US")) + suf;
      if (still || !isFinite(to)) { el.textContent = fmt(to); return; }
      const t0 = performance.now(), dur = 900;
      const tick = (t) => {
        const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
        el.textContent = fmt(to * e);
        if (k < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
  }
  const count = (v, dp = 0, suffix = "") => `<span data-count="${v}" data-dp="${dp}" data-suffix="${suffix}">${dp ? Number(v).toFixed(dp) : Number(v).toLocaleString("en-US")}${suffix}</span>`;

  // Tabs as steps: number keys and arrows move, the hash remembers, each pane animates on entry.
  function steps(n, onEnter) {
    const btns = [...document.querySelectorAll("#steps button")];
    let now = 1;
    function go(k) {
      k = Number(k);
      if (k < 1 || k > n) return;
      btns.forEach((b) => {
        const on = Number(b.dataset.step) === k;
        b.setAttribute("aria-selected", String(on));
        if (Number(b.dataset.step) === now && !on) b.classList.add("seen");
      });
      for (let i = 1; i <= n; i++) document.getElementById("pane-" + i).hidden = i !== k;
      now = k;
      try { history.replaceState(null, "", "#" + k); } catch (e) {}
      const pane = document.getElementById("pane-" + k);
      countIn(pane);
      if (onEnter) onEnter(k, pane);
    }
    btns.forEach((b) => b.addEventListener("click", () => go(b.dataset.step)));
    document.addEventListener("keydown", (e) => {
      if (e.target.matches("input, select, textarea") || e.metaKey || e.ctrlKey || e.altKey) return;
      if (new RegExp(`^[1-${n}]$`).test(e.key)) go(e.key);
      else if (e.key === "ArrowRight") go(now + 1);
      else if (e.key === "ArrowLeft") go(now - 1);
    });
    const h = Number(location.hash.replace("#", ""));
    return { go, now: () => now, start: () => go(h >= 1 && h <= n ? h : 1) };
  }

  function tools() {
    const big = document.getElementById("bigger"), theme = document.getElementById("theme");
    if (big) big.addEventListener("click", () => document.documentElement.classList.toggle("big"));
    if (theme) theme.addEventListener("click", () => {
      const r = document.documentElement, dark = r.dataset.theme === "dark" || (!r.dataset.theme && matchMedia("(prefers-color-scheme: dark)").matches);
      r.dataset.theme = dark ? "light" : "dark";
    });
  }
  tools();
  return { countIn, count, steps, still };
})();
