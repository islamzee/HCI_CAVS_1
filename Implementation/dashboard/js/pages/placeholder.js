// Starting point for a module page: shows the owner, the file to edit, and live values of the topics
// the module needs. Replace the page file (e.g. js/pages/map.js) with your own implementation.
// Author: Zeenat Islam

import { escapeHtml } from "../lib/format.js";

export function placeholder({ title, owner, file, sketch, topics }) {
  return {
    title,
    mount(root, { cavs }) {
      root.innerHTML = `
<div class="ph">
  <section class="panel"><h3>${escapeHtml(title.toUpperCase())}</h3>
    <p><b>Owner:</b> ${escapeHtml(owner)}<br><b>Sketch:</b> ${escapeHtml(sketch)}</p>
    <p>This page is a placeholder. Build the module in <code>${escapeHtml(file)}</code>, keeping the same shape:</p>
<pre>import { onEvents } from "../state.js";      // shared log, if you need it
export default {
  title: "${escapeHtml(title)}",
  mount(root, { cavs, state }) {
    root.innerHTML = \`&lt;section class="panel"&gt;…&lt;/section&gt;\`;
    const off = cavs.on("/mtx/odom", (d) =&gt; { … });
    return () =&gt; off();               // cleanup when leaving the page
  },
};</pre>
    <p>Shared pieces: <code>.panel</code>, <code>.kv</code>, <code>.btn</code>, <code>.dot</code> styles in <code>css/app.css</code>;
       clock and number formatting in <code>js/lib/format.js</code>; grid and map drawing in <code>js/lib/draw.js</code>
       (the Home page uses them). Field list: <code>Implementation/Frontend_Data_Guide_v1.md</code>.</p>
  </section>
  <section class="panel"><h3>LIVE DATA FOR THIS MODULE<span class="mute" style="font-size:13px;font-weight:500">messages received · latest value</span></h3>
    <div style="overflow:auto"><table><tbody>${topics.map((t) =>
      `<tr><td>${escapeHtml(t)}</td><td class="n" data-n="${escapeHtml(t)}">0</td><td class="v" data-v="${escapeHtml(t)}">waiting…</td></tr>`).join("")}</tbody></table></div>
  </section>
</div>`;
      const offs = topics.map((t) => {
        let n = 0;
        return cavs.on(t, (d) => {
          n++;
          const show = { ...d };
          for (const k of ["png", "jpeg"]) if (k in show) show[k] = "…";
          for (const k of ["poses", "points", "status"]) if (Array.isArray(show[k])) show[k] = `[${show[k].length}]`;
          root.querySelector(`[data-n="${CSS.escape(t)}"]`).textContent = n;
          root.querySelector(`[data-v="${CSS.escape(t)}"]`).textContent = JSON.stringify(show);
        });
      });
      return () => offs.forEach((off) => off());
    },
  };
}
