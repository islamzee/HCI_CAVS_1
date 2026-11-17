// Settings page. Owner: unassigned (first setting added by Zeenat). Author: Zeenat Islam
// Each setting is defined in js/settings.js; this page lists them as button groups.
// Planned (sketch): camera rate, fault thresholds, time format.

import { SETTINGS, getSetting, setSetting, resetSettings, onSettingChange } from "../settings.js";
import { escapeHtml } from "../lib/format.js";

export default {
  title: "Settings",
  mount(root) {
    root.innerHTML = `
<div class="settings">
  <section class="panel"><h3>SETTINGS<span class="actions"><button class="btn" id="reset">Reset to defaults</button></span></h3>
    ${Object.entries(SETTINGS).map(([key, s]) => `
    <div class="setting">
      <div><b>${escapeHtml(s.label)}</b><p class="mute">${escapeHtml(s.help)}</p></div>
      <div class="choices" data-key="${key}">${s.options.map((o) =>
        `<button class="btn" data-v="${o}">${o} ${escapeHtml(s.unit)}${o === s.default ? " (default)" : ""}</button>`).join("")}</div>
    </div>`).join("")}
    <p class="mute note">Saved in this browser only. Other settings from the sketch (camera rate, fault thresholds, time format) are not built yet.</p>
  </section>
</div>`;
    const show = () => root.querySelectorAll(".choices").forEach((g) =>
      g.querySelectorAll(".btn").forEach((b) => b.classList.toggle("on", +b.dataset.v === getSetting(g.dataset.key))));
    root.querySelectorAll(".choices .btn").forEach((b) =>
      (b.onclick = () => setSetting(b.parentElement.dataset.key, +b.dataset.v)));
    root.querySelector("#reset").onclick = resetSettings;
    show();
    return onSettingChange(show);
  },
};
