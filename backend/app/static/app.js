// Affiliate Autopilot — dashboard (vanilla JS, ไม่มี build step)
const $ = (s) => document.querySelector(s);
const api = async (path, opts) => {
  const r = await fetch("/api" + path, opts);
  if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
  return r.json();
};
const toast = (msg, err = false) => {
  const t = $("#toast");
  t.textContent = msg; t.className = "toast" + (err ? " err" : "");
  setTimeout(() => (t.className = "toast hidden"), 2600);
};

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
$("#btn-runall").onclick = async () => {
  const r = await api("/run-all", { method: "POST" });
  toast(`เริ่มรัน ${r.count} ร้าน — Claude+Gemini กำลังทำงานเบื้องหลัง`);
  setTimeout(loadAll, 4000);
};
$("#btn-sim").onclick = async () => {
  const r = await api("/metrics/simulate", { method: "POST" });
  toast(`จำลองผล ${r.simulated} โพสต์แล้ว`); loadAll();
};
$("#btn-opt").onclick = async () => {
  const r = await api("/auto-optimize", { method: "POST" });
  toast(`Auto-optimize: หยุด ${r.actions.length} ร้าน CTR ต่ำ`); loadAll();
};

// ---------------- KPIs
async function loadKpis() {
  const d = await api("/dashboard");
  const c = d.config;
  const sw = (ok) => `<span class="${ok ? "ok" : "dim"}">${ok ? "●" : "○"}</span>`;
  $("#kpis").innerHTML = `
    <div class="kpi"><div class="v">${d.stores_total}</div><div class="l">ร้านทั้งหมด</div>
      <div class="s"><span class="ok">${d.stores_active} active</span> · <span class="bad">${d.stores_paused} paused</span></div></div>
    <div class="kpi"><div class="v">${d.posts_total}</div><div class="l">โพสต์</div>
      <div class="s bad">${d.posts_failed} ล้มเหลว</div></div>
    <div class="kpi"><div class="v">${d.impressions.toLocaleString()}</div><div class="l">Impressions</div></div>
    <div class="kpi"><div class="v">${(d.ctr * 100).toFixed(2)}%</div><div class="l">CTR เฉลี่ย</div></div>
    <div class="kpi"><div class="v">฿${d.content_cost_baht}</div><div class="l">ค่า AI เขียน (สะสม)</div></div>
    <div class="kpi"><div class="l">สถานะระบบ</div>
      <div class="s">${sw(c.has_claude)} Claude · ${sw(c.has_gemini)} Gemini · ${sw(c.has_meta)} Meta</div>
      <div class="s dim">โหมด: ${c.posting_mode} · ${c.phones} เครื่อง · วีดีโอ ${c.video ? "เปิด" : "ปิด"}</div></div>`;
}

// ---------------- stores
async function renderStores() {
  const s = await api("/stores");
  $("#tab-stores").innerHTML = `<div class="grid">${s.map((x) => `
    <div class="card">
      <h4>${x.name}</h4>
      <div class="meta">${x.area || "—"} · ⭐${x.rating} (${x.review_count} รีวิว)</div>
      <div class="meta">เมนู: ${(x.menu || []).slice(0, 3).join(", ") || "—"}</div>
      <div class="row">
        <span class="badge ${x.status}">${x.status}${x.low_ctr_days ? " " + x.low_ctr_days + "วัน" : ""}</span>
        <button class="go" onclick="runStore(${x.id})">▶ รันร้านนี้</button>
      </div>
    </div>`).join("") || '<p class="muted">ยังไม่มีร้าน — ให้ n8n scraper ส่งเข้ามา หรือกด "รันครบวง"</p>'}</div>`;
}
window.runStore = async (id) => {
  await api(`/stores/${id}/run`, { method: "POST" });
  toast("เริ่มรันร้านนี้ — รอ Claude+Gemini สักครู่"); setTimeout(loadAll, 4000);
};

// ---------------- content + A/B
async function renderContent() {
  const s = await api("/stores");
  let html = "";
  for (const st of s.filter((x) => x.status !== "new").slice(0, 20)) {
    const c = await api(`/content/${st.id}`).catch(() => null);
    if (!c || !c.variants.length) continue;
    const ab = await api(`/abtest/${st.id}`).catch(() => ({ verdict: {} }));
    html += `<div class="card" style="margin-bottom:14px">
      <h4>${st.name}</h4>
      <div class="preview">${c.variants.map((v) => `
        <div class="v">
          ${v.media_url ? `<img class="media" src="${v.media_url}" />` : '<div class="media"></div>'}
          <div class="meta"><b>${v.platform}·${v.label}</b></div>
          <div style="font-size:12px">${v.hook}</div>
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
  $("#tab-posts").innerHTML = `<table><tr><th>เวลา</th><th>Platform</th><th>วิธี</th><th>บัญชี</th><th>สถานะ</th><th>ID</th></tr>
    ${p.map((x) => `<tr>
      <td class="muted">${x.posted_at ? new Date(x.posted_at).toLocaleString("th-TH") : "—"}</td>
      <td>${x.platform}</td>
      <td><span class="chip ${x.method}">${x.method}</span></td>
      <td class="muted">${x.account}</td>
      <td><span class="chip ${x.status}">${x.status}</span></td>
      <td class="muted">${x.external_id || x.error || ""}</td>
    </tr>`).join("") || '<tr><td colspan=6 class="muted">ยังไม่มีโพสต์</td></tr>'}</table>`;
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
    ["1. ดึงร้าน (n8n scraper)", "n8n รันทุก 6 ชม. → scrape Shopee Food → POST /api/ingest → กรอง rating≥4.5 + รีวิว≥20"],
    ["2. Claude เขียนคอนเทนต์", "ต่อร้าน → analysis + A/B variant (3 platform × 2 = 6 ชิ้น) + ตารางโพสต์ → JSON"],
    ["3. Gemini ทำสื่อ", "Nano Banana สร้างภาพ 9:16 (หรือ Veo ทำวีดีโอ) ต่อ variant"],
    ["4. โพสต์อัตโนมัติ (Hybrid)", "FB/IG ผ่าน Graph API · YouTube Data API · ตกหล่น→phone farm 6 เครื่อง · affiliate link คอมเมนต์แรก · สุ่ม delay 15–45 นาที"],
    ["5. Dashboard + Auto-optimize", "เก็บ metric → ตัดสิน A/B (ผู้ชนะต่อ platform) → ร้าน CTR ต่ำ 3 วันติด หยุดเอง ประหยัด cost"],
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
  await loadKpis().catch((e) => toast(e.message, true));
  const active = document.querySelector(".tabs button.active").dataset.tab;
  render(active);
}
loadAll();
setInterval(loadKpis, 15000);
