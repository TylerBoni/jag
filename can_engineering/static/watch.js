const grid = document.getElementById("grid");
const meta = document.getElementById("meta");
const rpmEl = document.getElementById("rpm");
const rpmVal = document.getElementById("rpm-val");
const gaugeByteEl = document.getElementById("gauge-byte");
const gaugeRawEl = document.getElementById("gauge-raw");
const gaugeVal = document.getElementById("gauge-val");
const gaugeSweepEl = document.getElementById("gauge-sweep");
const gaugeHint = document.getElementById("gauge-hint");
const oilEl = document.getElementById("oil");
const oilVal = document.getElementById("oil-val");
const id255RawEl = document.getElementById("id255-raw");
const id255TxVal = document.getElementById("id255-tx-value");
const id255TxEnabledEl = document.getElementById("id255-tx-enabled");
const enabledEl = document.getElementById("tx-enabled");
const txNote = document.getElementById("tx-note");
const tachDial = document.getElementById("tach-dial");
const dashRpm = document.getElementById("dash-rpm");
const steeringWheel = document.getElementById("steering-wheel");
const steeringValue = document.getElementById("steering-value");
const steeringZeroButton = document.getElementById("steering-zero");
const throttleFill = document.getElementById("throttle-fill");
const throttleValue = document.getElementById("throttle-value");
const gearDisplay = document.getElementById("gear-display");
const gearDetail = document.getElementById("gear-detail");
const gearTrack = document.getElementById("gear-track");
const paddleDown = document.getElementById("paddle-down");
const paddleUp = document.getElementById("paddle-up");
const paddleValue = document.getElementById("paddle-value");

let suppressSync = false;
let pending = null;
let flushTimer = null;
let currentSteeringRaw = null;
let steeringZero = Number(localStorage.getItem("steeringZero") || 0);

function ensureCard(idHex) {
  let el = document.getElementById(`card-${idHex}`);
  if (el) return el;
  el = document.createElement("article");
  el.className = "card";
  el.id = `card-${idHex}`;
  el.innerHTML = `
    <div class="card-head">
      <div class="title-row">
        <div class="title"></div>
        <div class="id"></div>
      </div>
      <div class="subtitle"></div>
      <div class="payload"></div>
    </div>
    <div class="signals"></div>
    <div class="note" hidden></div>
  `;
  grid.appendChild(el);
  return el;
}

function renderSignals(container, signals) {
  const existing = new Map(
    [...container.querySelectorAll(".sig")].map((el) => [el.dataset.key, el])
  );
  const seen = new Set();
  for (const sig of signals) {
    seen.add(sig.key);
    let el = existing.get(sig.key);
    if (!el) {
      el = document.createElement("div");
      el.className = "sig";
      el.dataset.key = sig.key;
      el.innerHTML = `
        <div class="sig-top">
          <span class="sig-label"></span>
          <span class="sig-text"></span>
        </div>
        <div class="bar"><span></span></div>
      `;
      container.appendChild(el);
    }
    el.classList.toggle("alert", !!sig.alert);
    el.classList.toggle("bool-yes", sig.kind === "bool" && sig.text === "Yes");
    el.classList.toggle("bool-no", sig.kind === "bool" && sig.text === "No");
    el.querySelector(".sig-label").textContent = sig.label;
    el.querySelector(".sig-text").textContent = sig.text;
    const bar = el.querySelector(".bar");
    bar.classList.toggle("enum", sig.kind === "enum");
    bar.classList.toggle("bool", sig.kind === "bool");
    bar.querySelector("span").style.width = `${sig.bar_pct || 0}%`;
  }
  for (const [key, el] of existing) {
    if (!seen.has(key)) el.remove();
  }
}

function applyGauge(c) {
  if (!c) return;
  const hex = Number(c.gauge_raw).toString(16).padStart(2, "0");
  gaugeVal.textContent = `0x4D5 byte ${c.gauge_byte} = ${hex}`;
  gaugeHint.textContent = `${c.sweep ? "Sweeping" : "Holding"}  ${c.frame_4d5 || ""}`;
  gaugeSweepEl.checked = !!c.sweep;
  gaugeByteEl.disabled = !!c.sweep;
  gaugeRawEl.disabled = !!c.sweep;
  if (c.sweep || !suppressSync) {
    gaugeByteEl.value = String(c.gauge_byte);
    gaugeRawEl.value = String(c.gauge_raw);
  }
}

function findSignal(state, key, maxAge = 1) {
  for (const row of state.rows || []) {
    if (Number(row.age) > maxAge) continue;
    const signal = (row.signals || []).find((item) => item.key === key);
    if (signal) return signal;
  }
  return null;
}

function decodeGear(modeSignal, manualSignal, selectorSignal) {
  if (modeSignal) {
    const mode = Number(modeSignal.phys);
    const manual = manualSignal ? Number(manualSignal.phys) : 0;
    if (mode === 0) return { gear: "P", detail: "Park" };
    if (mode === 1) return { gear: "R", detail: "Reverse" };
    if (mode === 2) return { gear: "N", detail: "Neutral" };
    if (mode === 4) return { gear: "D", detail: "Drive" };
    if (mode === 8) {
      const manualGears = new Map([
        [1, "M1"], [2, "M2"], [4, "M3"], [8, "M4"], [16, "M5"], [32, "M6"],
      ]);
      if (manualGears.has(manual)) {
        const gear = manualGears.get(manual);
        return { gear, detail: `Manual ${gear.slice(1)}` };
      }
      return { gear: "S", detail: "Sport" };
    }
    return { gear: String(mode), detail: modeSignal.text };
  }
  if (selectorSignal) {
    return {
      gear: String(Math.round(Number(selectorSignal.phys))),
      detail: `Selector code ${selectorSignal.text}`,
    };
  }
  return { gear: "—", detail: "Waiting for gear status" };
}

function renderCockpit(state) {
  const rpm = Math.max(0, Math.min(7000, Number(state.controls?.rpm || 0)));
  const rpmPct = (rpm / 7000) * 100;
  dashRpm.textContent = rpm.toLocaleString();
  tachDial.style.setProperty("--rpm-arc", `${rpmPct * 0.75}%`);
  tachDial.querySelector(".tach-needle").style.transform =
    `rotate(${-135 + rpmPct * 2.7}deg)`;

  const steering = findSignal(state, "i_SteeringAngle");
  if (steering && Math.abs(Number(steering.phys)) <= 900) {
    currentSteeringRaw = Number(steering.phys);
    const degrees = currentSteeringRaw - steeringZero;
    steeringWheel.style.transform = `rotate(${-degrees}deg)`;
    steeringValue.textContent = `${degrees.toFixed(1)}°`;
  } else {
    currentSteeringRaw = null;
    steeringWheel.style.transform = "rotate(0deg)";
    steeringValue.textContent = "Waiting…";
  }

  const throttle = findSignal(state, "i_ThrottlePosition");
  if (throttle) {
    const percent = Math.max(0, Math.min(100, Number(throttle.phys)));
    throttleFill.style.height = `${percent}%`;
    throttleValue.textContent = `${percent.toFixed(1)}%`;
  } else {
    throttleFill.style.height = "0%";
    const throttleFrame = (state.rows || []).find((row) => row.id === 0x2b5);
    throttleValue.textContent = throttleFrame
      ? "Decode unavailable"
      : "No 0x2B5 on bus";
  }

  const paddles = findSignal(state, "c_PaddleShifters");
  const paddleState = paddles ? Number(paddles.phys) : null;
  paddleDown.classList.toggle("active", paddleState === 225 || paddleState === 229);
  paddleUp.classList.toggle("active", paddleState === 228 || paddleState === 229);
  paddleValue.textContent = paddles
    ? paddles.text.replaceAll("_", " ")
    : "Paddles not seen";

  const gear = decodeGear(
    findSignal(state, "Mode"),
    findSignal(state, "ManualGear"),
    findSignal(state, "i_Gear"),
  );
  gearDisplay.textContent = gear.gear;
  gearDetail.textContent = gear.detail;
  const trackGear = gear.gear.startsWith("M") ? "S" : gear.gear;
  for (const item of gearTrack.querySelectorAll("[data-gear]")) {
    item.classList.toggle("active", item.dataset.gear === trackGear);
  }
}

function syncControlsFromServer(c) {
  if (!c) return;
  applyGauge(c);
  if (suppressSync) return;
  rpmEl.value = c.rpm;
  rpmVal.textContent = String(c.rpm);
  oilEl.value = String(c.oil_level);
  oilVal.textContent = c.oil_level_label;
  id255RawEl.value = String(c.coolant_raw_255);
  id255TxVal.textContent = `0x${Number(c.coolant_raw_255)
    .toString(16)
    .padStart(2, "0")}`;
  id255TxEnabledEl.checked = !!c.tx_255_enabled;
  enabledEl.checked = !!c.enabled;
  if (c.last_error) {
    txNote.textContent = c.last_error;
    txNote.classList.add("err");
  } else {
    txNote.textContent = c.enabled
      ? `Sending engine frames · ${c.tx_count} bursts`
      : c.tx_255_enabled
        ? `Sending 0x255 · ${c.tx_count} frames`
        : "TX off · Listening";
    txNote.classList.remove("err");
  }
}

function render4d5(state) {
  const card = document.getElementById("card-4d5");
  const status = document.getElementById("d5-status");
  const payload = document.getElementById("d5-payload");
  const bytesEl = document.getElementById("d5-bytes");
  const row = (state.rows || []).find((r) => r.id === 0x4d5);
  const data = row?.data || state.rx_4d5;
  card.classList.toggle("fresh", !!row?.fresh);
  if (!data || !data.length) {
    status.textContent = "Waiting for 0x4D5…";
    payload.textContent = "—";
    bytesEl.innerHTML = "";
    return;
  }
  const hz = row && row.hz >= 1 ? `${row.hz.toFixed(0)}× / sec` : "Heard";
  status.textContent = hz;
  payload.textContent = data.map((b) => b.toString(16).padStart(2, "0")).join(" ");
  bytesEl.innerHTML = data
    .map(
      (b, i) =>
        `<div class="byte"><span>b${i}</span><strong>${b.toString(16).padStart(2, "0")}</strong></div>`
    )
    .join("");
}

function render255(state) {
  const card = document.getElementById("card-255");
  const status = document.getElementById("id255-status");
  const payload = document.getElementById("id255-payload");
  const value = document.getElementById("id255-value");
  const bytesEl = document.getElementById("id255-bytes");
  const row = (state.rows || []).find((r) => r.id === 0x255);
  const data = row?.data;
  card.classList.toggle("fresh", !!row?.fresh);
  if (!data || !data.length) {
    status.textContent = "Waiting for 0x255…";
    payload.textContent = "—";
    value.textContent = "—";
    bytesEl.innerHTML = "";
    return;
  }
  status.textContent = row.hz >= 1 ? `${row.hz.toFixed(0)}× / sec` : "Heard";
  payload.textContent = data.map((b) => b.toString(16).padStart(2, "0")).join(" ");
  const b5 = data[5];
  const b7 = data[7];
  value.textContent =
    b5 == null || b7 == null
      ? "—"
      : `${b5.toString(16).padStart(2, "0")} / ${b7
          .toString(16)
          .padStart(2, "0")}  (${b5} / ${b7})`;
  bytesEl.innerHTML = data
    .map(
      (b, i) =>
        `<div class="byte${i === 5 || i === 7 ? " candidate" : ""}"><span>b${i}</span><strong>${b
          .toString(16)
          .padStart(2, "0")}</strong></div>`
    )
    .join("");
}

function render(state) {
  syncControlsFromServer(state.controls);
  renderCockpit(state);
  render4d5(state);
  render255(state);

  if (state.error) {
    meta.innerHTML = `<span class="err">${state.error}</span>`;
  } else {
    const nSig = state.rows.reduce((n, r) => n + (r.signals?.length || 0), 0);
    meta.textContent = `${state.id_count} groups · ${nSig} readings · ${
      state.running ? "live" : "stopped"
    }`;
  }

  if (!state.rows.length) {
    if (!grid.querySelector(".empty")) {
      grid.innerHTML = `<div class="empty">Waiting for car data… turn ignition on?</div>`;
    }
    return;
  }
  const empty = grid.querySelector(".empty");
  if (empty) empty.remove();

  const ordered = [...state.rows].sort(
    (a, b) => Number(b.has_decode) - Number(a.has_decode) || a.id - b.id
  );

  for (const row of ordered) {
    const card = ensureCard(row.id_hex);
    card.classList.toggle("fresh", row.fresh);
    card.querySelector(".title").textContent = row.name;
    card.querySelector(".id").textContent = row.id_hex;
    card.querySelector(".subtitle").textContent =
      row.hz >= 1 ? `Updating ${row.hz.toFixed(0)}× / sec` : "Quiet";
    card.querySelector(".payload").textContent = (row.data || [])
      .map((b) => b.toString(16).padStart(2, "0"))
      .join(" ");
    const sigBox = card.querySelector(".signals");
    const note = card.querySelector(".note");
    if (row.signals?.length) {
      renderSignals(sigBox, row.signals);
      note.hidden = true;
    } else {
      sigBox.innerHTML = "";
      note.hidden = true;
    }
  }
}

async function postControls(patch) {
  suppressSync = true;
  try {
    const res = await fetch("/api/controls", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    const c = await res.json();
    syncControlsFromServer(c);
  } catch (e) {
    txNote.textContent = "Could not update send values";
    txNote.classList.add("err");
  } finally {
    setTimeout(() => {
      suppressSync = false;
    }, 400);
  }
}

function queuePatch(patch) {
  pending = { ...(pending || {}), ...patch };
  clearTimeout(flushTimer);
  flushTimer = setTimeout(() => {
    const body = pending;
    pending = null;
    postControls(body);
  }, 80);
}

rpmEl.addEventListener("input", () => {
  rpmVal.textContent = rpmEl.value;
  queuePatch({ rpm: Number(rpmEl.value) });
});
steeringZeroButton.addEventListener("click", () => {
  if (currentSteeringRaw == null) return;
  steeringZero = currentSteeringRaw;
  localStorage.setItem("steeringZero", String(steeringZero));
  steeringWheel.style.transform = "rotate(0deg)";
  steeringValue.textContent = "0.0°";
});
gaugeByteEl.addEventListener("change", () => {
  gaugeSweepEl.checked = false;
  queuePatch({ gauge_byte: Number(gaugeByteEl.value), sweep: false });
});
gaugeRawEl.addEventListener("input", () => {
  const hex = Number(gaugeRawEl.value).toString(16).padStart(2, "0");
  gaugeVal.textContent = `0x4D5 byte ${gaugeByteEl.value} = ${hex}`;
  gaugeSweepEl.checked = false;
  queuePatch({
    gauge_byte: Number(gaugeByteEl.value),
    gauge_raw: Number(gaugeRawEl.value),
    sweep: false,
  });
});
gaugeSweepEl.addEventListener("change", () => {
  postControls({ sweep: gaugeSweepEl.checked });
});
oilEl.addEventListener("change", () => {
  oilVal.textContent = oilEl.options[oilEl.selectedIndex].text;
  queuePatch({ oil_level: Number(oilEl.value) });
});
id255RawEl.addEventListener("input", () => {
  const raw = Number(id255RawEl.value);
  id255TxVal.textContent = `0x${raw.toString(16).padStart(2, "0")}`;
  queuePatch({ coolant_raw_255: raw });
});
id255TxEnabledEl.addEventListener("change", () => {
  postControls({ tx_255_enabled: id255TxEnabledEl.checked });
});
enabledEl.addEventListener("change", () => {
  postControls({ enabled: enabledEl.checked });
});

async function tick() {
  try {
    const res = await fetch("/api/state", { cache: "no-store" });
    render(await res.json());
  } catch (e) {
    meta.innerHTML = `<span class="err">Lost connection to app</span>`;
  }
}

setInterval(tick, 120);
tick();
