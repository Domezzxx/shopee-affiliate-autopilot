// Affiliate Autopilot — dashboard (vanilla JS, ไม่มี build step)
const $ = (s) => document.querySelector(s);
const api = async (path, opts) => {
  const r = await fetch("/api" + path, opts);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
};
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const toast = (msg, err = false) => {
  const t = $("#toast");
  t.textContent = msg; t.className = "toast" + (err ? " err" : "");
  setTimeout(() => (t.className = "toast hidden"), 2800);
};

let showAddForm = false;

// ---------------- progress การสร้างคลิป AI
let progressTimer = null, progressRefreshed = false;
function renderProgress(jobs) {
  const box = $("#progress");
  if (!jobs || !jobs.length) { box.className = "hidden"; box.innerHTML = ""; return; }
  box.className = "";
  box.innerHTML = `<div class="phead"><span class="pspin"></span> กำลังสร้างคลิป AI · ${jobs.length} ร้าน</div>` +
    jobs.map((j) => `
    <div class="pjob ${j.status}">
      <div class="ptop">
        <span class="pname">${esc(j.name)}</span>
        <span class="pstep">${esc(j.step)}${j.detail ? " · " + esc(j.detail) : ""} · ${j.pct}%</span>
      </div>
      <div class="pbar"><div class="pfill" style="width:${j.pct}%"></div></div>
    </div>`).join("");
}
async function pollProgress() {
  let jobs = [];
  try { jobs = (await api("/progress")).jobs || []; } catch (e) { return; }
  renderProgress(jobs);
  const active = jobs.some((j) => j.status === "running");
  if (active) progressRefreshed = false;
  else if (jobs.length && !progressRefreshed) { progressRefreshed = true; loadAll(); }  // เสร็จ → refresh 1 ครั้ง
  if (!jobs.length && progressTimer) { clearInterval(progressTimer); progressTimer = null; }
}
function startProgress() {
  progressRefreshed = false;
  if (!progressTimer) progressTimer = setInterval(pollProgress, 1200);
  pollProgress();
}

// ---------------- tabs
document.querySelectorAll(".tabs button").forEach((b) =>
  b.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((x) => x.classList.remove("active"));
    document.querySelectorAll(".panel").forEach((x) => x.classList.add("hidden"));
    b.classList.add("active");
    $("#tab-" + b.dataset.tab).classList.remove("hidden");
    render(b.dataset.tab);
  })
);

// ---------------- actions
$("#btn-add").onclick = () => {
  showAddForm = !showAddForm;
  document.querySelector('.tabs button[data-tab="stores"]').click();
};
$("#btn-runall").onclick = async () => {
  const r = await api("/run-all", { method: "POST" });
  toast(`เริ่มรัน ${r.count} ร้าน — ดูความคืบหน้าด้านบน`);
  startProgress();
};
$("#btn-sim").onclick = async () => {
  const r = await api("/metrics/simulate", { method: "POST" });
  toast(`จำลองผล ${r.simulated} โพสต์แล้ว`); loadAll();
};
$("#btn-opt").onclick = async () => {
  const r = await api("/auto-optimize", { method: "POST" });
  toast(`Auto-optimize: หยุด ${r.actions.length} ร้าน CTR ต่ำ`); loadAll();
};
$("#btn-preflight").onclick = async () => {
  const p = await api("/post/preflight");
  const row = (name, x) => `${x.live ? "🟢" : "🔴"} ${name}: ${x.detail}`;
  const lines = [
    `🚦 ${p.summary}`, "",
    row("Facebook", p.facebook),
    row("Instagram", p.instagram),
    row("YouTube", p.youtube),
    "", `โหมดโพสต์: ${p.posting_mode} · หน่วงเวลา: ${p.post_delay ? "เปิด" : "ปิด"}`,
  ];
  alert(lines.join("\n"));
};

// ---------------- system on/off (master switch)
let systemEnabled = true;
function healthTip(h) {
  if (!h) return "";
  const yn = (v) => (v ? "✓" : "✗");
  return [
    `AI เขียนคอนเทนต์: ${yn(h.content_ai)}`,
    `Flow video (Chrome debug): ${yn(h.flow_chrome)}`,
    `มือถือ phone farm: ${h.phone_devices} เครื่อง`,
    `Pexels: ${yn(h.stock_video)} · Freesound: ${yn(h.ambience_sfx)}`,
    `Meta: ${yn(h.meta)} · YouTube: ${yn(h.youtube)} · โหมด: ${h.posting_mode}`,
  ].join("\n");
}
async function loadSystem() {
  try {
    const s = await api("/system");
    systemEnabled = s.enabled;
    const b = $("#btn-system");
    b.textContent = s.enabled ? "🟢 ระบบเปิด" : "🔴 ระบบปิด";
    b.className = "sys " + (s.enabled ? "on" : "off");
    b.title = healthTip(s.health);
  } catch (e) {}
}
$("#btn-system").onclick = async () => {
  const next = !systemEnabled;
  if (!next && !confirm("ปิดระบบ? บอทจะหยุดรัน/โพสต์อัตโนมัติ\n(เปิดใหม่ทำงานต่อได้ปกติ)")) return;
  try {
    const r = await api(`/system/toggle?enable=${next}`, { method: "POST" });
    systemEnabled = r.enabled;
    toast(r.enabled ? "🟢 เปิดระบบแล้ว — บอทพร้อมทำงาน" : "🔴 ปิดระบบแล้ว — บอทหยุดทำงานอัตโนมัติ");
    loadSystem();
  } catch (e) { toast(e.message, true); }
};

// ---------------- banner (real vs mock)
async function loadBanner() {
  const k = await api("/keys/status");
  if (k.real_mode) {
    const brain = k.content_provider === "gemini" ? "Gemini (ฟรี)" : "Claude";
    $("#banner").innerHTML = `<div class="banner real">🟢 REAL MODE — เขียนด้วย ${brain} · ภาพ Gemini${k.meta ? " · Meta พร้อม" : ""} · โพสต์: ${k.posting_mode}</div>`;
  } else if (k.content_provider === "gemini") {
    $("#banner").innerHTML = `<div class="banner mock">🟡 โหมด MOCK — ใส่ <b>GEMINI_API_KEY</b> (ฟรี) ใน .env แล้วรัน run_local.ps1 ใหม่ → ทดสอบจริงฟรี ฿0</div>`;
  } else {
    $("#banner").innerHTML = `<div class="banner mock">🟡 โหมด MOCK — อยากทดสอบฟรี: ตั้ง <b>CONTENT_PROVIDER=gemini</b> + ใส่ <b>GEMINI_API_KEY</b> ใน .env (ไม่ต้องใช้ Claude)</div>`;
  }
}

// ---------------- KPIs
async function loadKpis() {
  const d = await api("/dashboard");
  const c = d.config;
  const sw = (ok) => `<span class="${ok ? "ok" : "dim"}">${ok ? "●" : "○"}</span>`;
  const profitColor = d.profit_baht >= 0 ? "ok" : "bad";
  const profitSign = d.profit_baht >= 0 ? "+฿" : "-฿";
  $("#kpis").innerHTML = `
    <div class="kpi"><div class="v">${d.stores_total}</div><div class="l">ร้านทั้งหมด</div>
      <div class="s"><span class="ok">${d.stores_active} active</span> · <span class="bad">${d.stores_paused} paused</span></div></div>
    <div class="kpi"><div class="v">${d.posts_total}</div><div class="l">โพสต์</div>
      <div class="s bad">${d.posts_failed} ล้มเหลว</div></div>
    <div class="kpi"><div class="v">฿${d.revenue_baht.toLocaleString()}</div><div class="l">รายได้ประเมิน</div>
      <div class="s ${profitColor}">${profitSign}${Math.abs(d.profit_baht).toLocaleString()} กำไรสุทธิ</div></div>
    <div class="kpi"><div class="v">${d.impressions.toLocaleString()}</div><div class="l">Impressions</div></div>
    <div class="kpi"><div class="v">${(d.ctr * 100).toFixed(2)}%</div><div class="l">CTR เฉลี่ย</div></div>
    <div class="kpi"><div class="v">฿${d.content_cost_baht}</div><div class="l">ค่า AI เขียน (สะสม)</div></div>
    <div class="kpi"><div class="l">สถานะระบบ</div>
      <div class="s">${sw(c.has_claude)} Claude · ${sw(c.has_gemini)} Gemini · ${sw(c.has_meta)} Meta</div>
      <div class="s dim">โหมด: ${c.posting_mode} · ${c.phones} เครื่อง · วีดีโอ ${c.video ? "เปิด" : "ปิด"}</div></div>`;
}

// ---------------- stores (+ add form)
function addFormHTML() {
  if (!showAddForm) return "";
  return `<div class="card addform">
    <h4>เพิ่มร้านเอง</h4>
    <div class="formgrid">
      <input id="f-name" placeholder="ชื่อร้าน *" />
      <input id="f-area" placeholder="ย่าน เช่น อุดรธานี" />
      <input id="f-rating" type="number" step="0.1" placeholder="เรตติ้ง เช่น 4.7" />
      <input id="f-reviews" type="number" placeholder="จำนวนรีวิว เช่น 120" />
      <input id="f-price" placeholder="ช่วงราคา เช่น 40-80 บาท" />
      <input id="f-menu" placeholder="เมนู (คั่นด้วย , )" />
      <input id="f-link" placeholder="affiliate link" />
      <input id="f-shopee" placeholder="Shopee URL (ถ้ามี)" />
    </div>
    <div class="row" style="margin-top:10px">
      <span class="muted">เพิ่มเองไม่ติดเกณฑ์กรอง · หรืออัปโหลด CSV ด้านขวา</span>
      <span>
        <label class="btn-file">📄 อัปโหลด CSV<input id="f-csv" type="file" accept=".csv" hidden /></label>
        <button class="go" id="f-submit">บันทึก + รันร้านนี้</button>
      </span>
    </div>
  </div>`;
}

async function renderStores() {
  const s = await api("/stores");
  $("#tab-stores").innerHTML = addFormHTML() + `<div class="grid">${s.map((x) => `
    <div class="card">
      <h4>${esc(x.name)}</h4>
      <div class="meta">${esc(x.area) || "—"} · ⭐${x.rating} (${x.review_count} รีวิว)</div>
      <div class="meta">เมนู: ${esc((x.menu || []).slice(0, 3).join(", ")) || "—"}</div>
      <div class="meta">${x.affiliate_link ? "🔗 มีลิงก์" : '<span class="bad">⚠ ยังไม่มีลิงก์</span>'}</div>
      <div class="meta" style="margin-top:6px; font-weight:600">
        <span>ทุน: ฿${x.cost}</span> · 
        <span class="${x.profit >= 0 ? 'ok' : 'bad'}">กำไร: ฿${x.profit}</span>
      </div>
      <div class="meta" style="margin-top:6px">
        <label style="cursor:pointer; display:flex; align-items:center; gap:6px; user-select:none">
          <input type="checkbox" ${x.requires_approval ? "checked" : ""} onchange="toggleApproval(${x.id}, this.checked)" />
          ต้องการอนุมัติก่อนโพสต์
        </label>
      </div>
      <div class="row" style="margin-top:10px">
        <span class="badge ${x.status}">${x.status}${x.low_ctr_days ? " " + x.low_ctr_days + "วัน" : ""}</span>
        <button class="go" onclick="runStore(${x.id})">▶ รันร้านนี้</button>
      </div>
    </div>`).join("") || '<p class="muted">ยังไม่มีร้าน — กด "+ เพิ่มร้าน" / อัปโหลด CSV / ให้ n8n scraper ส่งเข้ามา</p>'}</div>`;

  if (showAddForm) {
    $("#f-submit").onclick = submitAddStore;
    $("#f-csv").onchange = submitCsv;
  }
}
async function submitAddStore() {
  const body = {
    name: $("#f-name").value.trim(),
    area: $("#f-area").value.trim(),
    rating: parseFloat($("#f-rating").value) || 0,
    review_count: parseInt($("#f-reviews").value) || 0,
    price_range: $("#f-price").value.trim(),
    menu: $("#f-menu").value.split(",").map((x) => x.trim()).filter(Boolean),
    affiliate_link: $("#f-link").value.trim(),
    shopee_url: $("#f-shopee").value.trim(),
  };
  if (!body.name) return toast("ใส่ชื่อร้านก่อน", true);
  try {
    const r = await api("/stores/add", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    toast(`เพิ่ม "${r.name}" แล้ว — กำลังรันร้านนี้`);
    await api(`/stores/${r.id}/run`, { method: "POST" });
    showAddForm = false;
    loadAll(); startProgress();
  } catch (e) { toast(e.message, true); }
}
async function submitCsv(ev) {
  const file = ev.target.files[0];
  if (!file) return;
  const fd = new FormData(); fd.append("file", file);
  try {
    const r = await api("/ingest/csv", { method: "POST", body: fd });
    toast(`CSV: เพิ่ม ${r.added} ร้าน / ข้าม ${r.skipped}`);
    loadAll();
  } catch (e) { toast(e.message, true); }
}
window.runStore = async (id) => {
  await api(`/stores/${id}/run`, { method: "POST" });
  toast("เริ่มรันร้านนี้ — ดูความคืบหน้าด้านบน"); startProgress();
};
window.makeReel = async (id, label = "A") => {
  const voice = document.getElementById(`voice-sel-${id}`)?.value || "female";
  const vlabel = voice === "male" ? "เสียงผู้ชาย" : "เสียงผู้หญิง";
  try {
    await api(`/stores/${id}/reel?label=${label}&voice=${voice}`, { method: "POST" });
    toast(`เริ่มรวมคลิป ${label} (${vlabel}) — ดูความคืบหน้าด้านบน`);
    startProgress();
  } catch (e) { toast(e.message, true); }
};
window.makeRestaurant = async (id) => {
  try {
    await api(`/stores/${id}/restaurant-reel?voice=male`, { method: "POST" });
    toast("เริ่มทำรีวิวในร้าน (พ่อครัวพูด) — ดูความคืบหน้าด้านบน · ~1-2 นาที");
    startProgress();
  } catch (e) { toast(e.message, true); }
};
window.toggleApproval = async (id, enable) => {
  try {
    await api(`/stores/${id}/toggle-approval?enable=${enable}`, { method: "POST" });
    toast("อัปเดตการตั้งค่าการอนุมัติแล้ว");
    loadAll();
  } catch (e) { toast(e.message, true); }
};
window.approveJob = async (id) => {
  try {
    await api(`/jobs/${id}/approve`, { method: "POST" });
    toast("อนุมัติงานและกำลังโพสต์เบื้องหลัง...");
    loadAll(); startProgress();
  } catch (e) { toast(e.message, true); }
};

// ---------------- content + A/B
async function renderContent() {
  const s = await api("/stores");
  let html = "";
  for (const st of s.filter((x) => x.status !== "new").slice(0, 20)) {
    const c = await api(`/content/${st.id}`).catch(() => null);
    if (!c || !c.variants.length) continue;
    const latestJob = c.jobs[0] || {};
    const isPending = latestJob.status === "pending_approval";
    const ab = await api(`/abtest/${st.id}`).catch(() => ({ verdict: {} }));
    html += `<div class="card" style="margin-bottom:14px">
      <div class="row"><h4>${esc(st.name)}</h4>
        <span>
          ${isPending ? `<button class="primary" style="margin-right:6px" onclick="approveJob(${latestJob.id})">✅ อนุมัติ & โพสต์</button>` : ""}
          <select id="voice-sel-${st.id}" class="voicesel">
            <option value="female">👩 เสียงผู้หญิง</option>
            <option value="male">👨 เสียงผู้ชาย</option>
          </select>
          <button class="go" onclick="makeReel(${st.id},'A')">🎬 รวมคลิป A</button>
          <button class="go" onclick="makeReel(${st.id},'B')">🎬 รวมคลิป B</button>
          <button class="primary" onclick="makeRestaurant(${st.id})">🍜 รีวิวในร้าน</button>
        </span></div>
      ${isPending ? `<div class="banner mock" style="margin:8px 0 12px 0">⏳ คอนเทนต์ผลิตเสร็จแล้ว กำลังรอคุณอนุมัติเพื่อยิงโพสต์ออกไปยังแพลตฟอร์มต่าง ๆ</div>` : ""}
      ${c.reel_url ? `<div class="reelwrap"><div class="meta" style="margin-bottom:4px">คลิปรวม (montage) — โพสต์ได้เลย</div>
        <video class="reel" src="${c.reel_url}" controls loop playsinline></video></div>` : ""}
      <div class="preview">${c.variants.map((v) => `
        <div class="v">
          ${!v.media_url ? '<div class="media"></div>'
            : v.media_type === "video"
              ? `<video class="media" src="${v.media_url}" muted loop playsinline controls></video>`
              : `<img class="media" src="${v.media_url}" />`}
          <div class="meta"><b>${v.platform}·${v.label}</b>${v.media_type === "video" ? ' <span class="chip posted">วีดีโอ</span>' : ""}</div>
          <div style="font-size:12px">${esc(v.hook)}</div>
          ${v.first_comment ? `<div class="fc">💬 ${esc(v.first_comment)}</div>` : ""}
        </div>`).join("")}</div>
      ${renderAB(ab)}
    </div>`;
  }
  $("#tab-content").innerHTML = html || '<p class="muted">ยังไม่มีคอนเทนต์ — กด "รันครบวง" ก่อน</p>';
}
function renderAB(ab) {
  if (!ab.by_platform) return "";
  return Object.entries(ab.by_platform).map(([plat, sides]) => {
    const v = ab.verdict[plat] || {};
    const A = sides.A, B = sides.B; if (!A || !B) return "";
    const max = Math.max(A.ctr, B.ctr, 0.001);
    const cell = (lab, x, win) => `<div class="side ${win ? "win" : ""}">
      <b>${lab}${win ? " 🏆" : ""}</b> · CTR ${(x.ctr * 100).toFixed(2)}%
      <div class="meta">${x.impressions} imp · ${x.clicks} clk</div>
      <div class="bar"><span style="width:${(x.ctr / max) * 100}%"></span></div></div>`;
    return `<div style="margin-top:6px"><div class="meta">${plat} ${v.ready ? "" : "(กำลังเก็บข้อมูล)"}</div>
      <div class="ab">${cell("A", A, v.winner === "A")}${cell("B", B, v.winner === "B")}</div></div>`;
  }).join("");
}

// ---------------- posts
async function renderPosts() {
  const p = await api("/posts");
  $("#tab-posts").innerHTML = `<table><tr><th>เวลา</th><th>Platform</th><th>วิธี</th><th>บัญชี</th><th>สถานะ</th><th>คอมเมนต์ลิงก์</th><th>ID</th></tr>
    ${p.map((x) => `<tr>
      <td class="muted">${x.posted_at ? new Date(x.posted_at).toLocaleString("th-TH") : "—"}</td>
      <td>${x.platform}</td>
      <td><span class="chip ${x.method}">${x.method}</span></td>
      <td class="muted">${esc(x.account)}</td>
      <td><span class="chip ${x.status}">${x.status}</span></td>
      <td>${x.comment_status ? `<span class="chip ${x.comment_status === "posted" ? "posted" : "failed"}">${x.comment_status}</span>` : "—"}</td>
      <td class="muted">${esc(x.external_id || x.error || "")}</td>
    </tr>`).join("") || '<tr><td colspan=7 class="muted">ยังไม่มีโพสต์</td></tr>'}</table>`;
}

// ---------------- platform performance
async function renderPlatform() {
  const d = await api("/dashboard");
  const e = Object.entries(d.by_platform);
  $("#tab-platform").innerHTML = `<div class="grid">${e.map(([p, v]) => `
    <div class="card"><h4>${p}</h4>
      <div class="row"><span class="muted">CTR</span><b class="${v.ctr > 0.01 ? "ok" : "bad"}">${(v.ctr * 100).toFixed(2)}%</b></div>
      <div class="row"><span class="muted">Impressions</span><b>${v.impressions.toLocaleString()}</b></div>
      <div class="row"><span class="muted">Clicks</span><b>${v.clicks.toLocaleString()}</b></div>
    </div>`).join("") || '<p class="muted">ยังไม่มีข้อมูลผล — กด "จำลองผล" เพื่อดูเดโม</p>'}</div>`;
}

// ---------------- flow diagram
function renderFlow() {
  const steps = [
    ["1. ดึงร้าน (n8n scraper / เพิ่มเอง / CSV)", "n8n รันทุก 6 ชม. → POST /api/ingest → กรอง rating≥4.5 + รีวิว≥20 · หรือเพิ่มเอง/อัปโหลด CSV"],
    ["2. Claude เขียนคอนเทนต์", "ต่อร้าน → analysis + A/B variant (6 ชิ้น) + คอมเมนต์แรก (affiliate link) + ตารางโพสต์"],
    ["3. Gemini ทำสื่อ", "Nano Banana สร้างภาพ 9:16 (หรือ Veo ทำวีดีโอ) ต่อ variant"],
    ["4. โพสต์อัตโนมัติ (Hybrid)", "FB/IG Graph API · YouTube · ตกหล่น→phone farm · วาง affiliate link เป็นคอมเมนต์แรกทันที"],
    ["5. Dashboard + Auto-optimize", "เก็บ metric → ตัดสิน A/B (ผู้ชนะต่อ platform) → ร้าน CTR ต่ำ 3 วันติด หยุดเอง"],
  ];
  $("#tab-flow").innerHTML = steps.map((s) =>
    `<div class="flowstep"><b>${s[0]}</b><div class="muted" style="margin-top:4px">${s[1]}</div></div>`).join("");
}

// ---------------- driver
function render(tab) {
  ({ stores: renderStores, content: renderContent, posts: renderPosts,
     platform: renderPlatform, flow: renderFlow }[tab] || (() => {}))();
}
async function loadAll() {
  await Promise.all([loadSystem().catch(() => {}), loadBanner().catch(() => {}), loadKpis().catch((e) => toast(e.message, true))]);
  const active = document.querySelector(".tabs button.active").dataset.tab;
  render(active);
}
loadAll();
startProgress();   // เผื่อมีงานสร้างคลิปค้างอยู่ตอนเปิด/รีเฟรชหน้า
setInterval(loadKpis, 15000);
