// Affiliate Autopilot — dashboard (vanilla JS, ไม่มี build step)
const $ = (s) => document.querySelector(s);

// เลิกใช้ "เชื่อมต่อ API" ภายนอก — เปิดผ่าน Tailscale Funnel/local = origin เดียวกับ backend
let backendUrl = "";
try { localStorage.removeItem("backend_url"); } catch (e) {}   // เคลียร์ค่าเก่า (กัน URL ตายค้าง)

const getApiUrl = (path) => {
  return (backendUrl ? backendUrl : "") + "/api" + path;
};

const getMediaUrl = (url) => {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return (backendUrl ? backendUrl : "") + url;
};

const api = async (path, opts) => {
  const r = await fetch(getApiUrl(path), opts);
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
  if (r.status === "started_with_scrape") {
    toast(`ไม่พบร้านค้าใหม่ กำลังเริ่มดึงร้านและสร้างคลิปอัตโนมัติ — ดูความคืบหน้าด้านบน`);
  } else {
    toast(`เริ่มรัน ${r.count} ร้าน — ดูความคืบหน้าด้านบน`);
  }
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
let autopilotOn = false;
async function loadSystem() {
  try {
    const s = await api("/system");
    systemEnabled = s.enabled;
    autopilotOn = s.health?.autopilot;
    const b = $("#btn-system");
    b.textContent = s.enabled ? "🟢 ระบบเปิด" : "🔴 ระบบปิด";
    b.className = "sys " + (s.enabled ? "on" : "off");
    b.title = healthTip(s.health);
    const a = $("#btn-autopilot");
    a.textContent = autopilotOn ? "🤖 Auto: เปิด" : "🤖 Auto: ปิด";
    a.className = "sys " + (autopilotOn ? "on" : "off");
    a.title = "Auto-Pilot: ประมวลผลร้านใหม่เองตามรอบ" + (s.health?.flow_blocked ? " · ⚠️ Flow เครดิตหมด (พักอยู่)" : "");
  } catch (e) {}
}
$("#btn-autopilot").onclick = async () => {
  try {
    const r = await api(`/system/autopilot?enable=${!autopilotOn}`, { method: "POST" });
    toast(r.autopilot ? "🤖 เปิด Auto-Pilot — ระบบจะประมวลผลร้านใหม่เองตามรอบ" : "🤖 ปิด Auto-Pilot");
    loadSystem();
  } catch (e) { toast(e.message, true); }
};
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
  const isLocal = location.hostname === "localhost" || location.hostname === "127.0.0.1" || location.hostname.startsWith("192.168.");
  try {
    const k = await api("/keys/status");
    const suffix = backendUrl ? " (ผ่าน Tunnel)" : "";
    if (k.real_mode) {
      const brain = k.content_provider === "gemini" ? "Gemini (ฟรี)" : "Claude";
      $("#banner").innerHTML = `<div class="banner real">🟢 REAL MODE — เขียนด้วย ${brain} · ภาพ Gemini${k.meta ? " · Meta พร้อม" : ""} · โพสต์: ${k.posting_mode}${suffix}</div>`;
    } else if (k.content_provider === "gemini") {
      $("#banner").innerHTML = `<div class="banner mock">🟡 โหมด MOCK — ใส่ <b>GEMINI_API_KEY</b> (ฟรี) ใน .env แล้วรัน run_local.ps1 ใหม่ → ทดสอบจริงฟรี ฿0${suffix}</div>`;
    } else {
      $("#banner").innerHTML = `<div class="banner mock">🟡 โหมด MOCK — อยากทดสอบฟรี: ตั้ง <b>CONTENT_PROVIDER=gemini</b> + ใส่ <b>GEMINI_API_KEY</b> ใน .env (ไม่ต้องใช้ Claude)${suffix}</div>`;
    }
  } catch (e) {
    $("#banner").innerHTML = `<div class="banner mock" style="background:#3a1a1a; border-color:var(--accent); color:#fff; font-weight:600;">🔴 <b>ไม่สามารถเชื่อมต่อกับ API Backend ได้</b> — เช็คว่า server (:8088) รันอยู่ไหม</div>`;
    throw e;
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
      <select id="f-category">
        <option value="food">🍜 ร้านอาหาร</option>
        <option value="gadget">🛒 ร้านอุปกรณ์ (IT/ของใช้บ้าน)</option>
      </select>
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

let storeCatFilter = "";   // "" = ทั้งหมด | food | gadget
const CAT_LABEL = { food: "🍜 ร้านอาหาร", gadget: "🛒 ร้านอุปกรณ์" };
const CAT_COLOR = { food: "#e67e22", gadget: "#2980b9" };
function setStoreCat(c) { storeCatFilter = c; renderStores(); }

async function renderStores() {
  const all = await api("/stores");
  const catOf = (x) => x.category || "food";
  const cnt = { all: all.length, food: all.filter((x) => catOf(x) === "food").length,
                gadget: all.filter((x) => catOf(x) === "gadget").length };
  const s = storeCatFilter ? all.filter((x) => catOf(x) === storeCatFilter) : all;
  const btn = (c, label) => `<button onclick="setStoreCat('${c}')" style="padding:6px 14px;border-radius:20px;cursor:pointer;border:1px solid var(--line);${storeCatFilter === c ? "background:#3a4150;color:#fff;font-weight:600" : "background:#2a2f3a;color:var(--txt)"}">${label}</button>`;
  const bar = `<div style="display:flex;gap:8px;margin:4px 0 14px;flex-wrap:wrap">
    ${btn("", "ทั้งหมด (" + cnt.all + ")")}
    ${btn("food", "🍜 ร้านอาหาร (" + cnt.food + ")")}
    ${btn("gadget", "🛒 ร้านอุปกรณ์ (" + cnt.gadget + ")")}
  </div>`;
  $("#tab-stores").innerHTML = addFormHTML() + bar + `<div class="grid">${s.map((x) => `
    <div class="card">
      <h4><span style="display:inline-block;font-size:11px;padding:1px 8px;border-radius:10px;color:#fff;background:${CAT_COLOR[catOf(x)] || "#777"};margin-right:6px;vertical-align:middle">${CAT_LABEL[catOf(x)] || catOf(x)}</span>${esc(x.name)}</h4>
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
    category: ($("#f-category") && $("#f-category").value) || "food",
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
  const filterMonth = $("#content-filter-month").value;
  const filterPlatform = $("#content-filter-platform").value;

  const s = await api("/stores");
  let html = "";
  for (const st of s.filter((x) => x.status !== "new").slice(0, 20)) {
    const c = await api(`/content/${st.id}`).catch(() => null);
    if (!c || !c.variants.length) continue;

    // Filter variants based on platform and creation month
    let variants = c.variants;
    if (filterPlatform) {
      variants = variants.filter((v) => v.platform === filterPlatform);
    }
    if (filterMonth) {
      variants = variants.filter((v) => {
        if (!v.created_at) return false;
        const d = new Date(v.created_at);
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const yyyymm = `${yyyy}-${mm}`;
        return yyyymm === filterMonth;
      });
    }

    // Skip store card entirely if no variants match
    if (!variants.length) continue;

    const latestJob = c.jobs[0] || {};
    const isPending = latestJob.status === "pending_approval";
    const ab = await api(`/abtest/${st.id}`).catch(() => ({ verdict: {} }));
    
    // Filter A/B test results to match platform filter if applicable
    let abHtml = "";
    if (filterPlatform) {
      const filteredAb = { verdict: {}, by_platform: {} };
      if (ab.by_platform && ab.by_platform[filterPlatform]) {
        filteredAb.by_platform[filterPlatform] = ab.by_platform[filterPlatform];
        filteredAb.verdict[filterPlatform] = ab.verdict[filterPlatform];
      }
      abHtml = renderAB(filteredAb);
    } else {
      abHtml = renderAB(ab);
    }

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
        <video class="reel" src="${getMediaUrl(c.reel_url)}" controls loop playsinline></video></div>` : ""}
      <div class="preview">${variants.map((v) => `
        <div class="v">
          ${!v.media_url ? '<div class="media"></div>'
            : v.media_type === "video"
              ? `<video class="media" src="${getMediaUrl(v.media_url)}" muted loop playsinline controls></video>`
              : `<img class="media" src="${getMediaUrl(v.media_url)}" />`}
          <div class="meta"><b>${v.platform}·${v.label}</b>${v.media_type === "video" ? ' <span class="chip posted">วีดีโอ</span>' : ""}</div>
          <div style="font-size:12px">${esc(v.hook)}</div>
          ${v.first_comment ? `<div class="fc">💬 ${esc(v.first_comment)}</div>` : ""}
        </div>`).join("")}</div>
      ${abHtml}
    </div>`;
  }
  $("#content-list").innerHTML = html || '<p class="muted">ไม่พบข้อมูลคอนเทนต์ที่ตรงกับตัวกรอง</p>';
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
  const filterMonth = $("#posts-filter-month").value;
  const filterDate = $("#posts-filter-date").value;
  const filterPlatform = $("#posts-filter-platform").value;
  const filterStatus = $("#posts-filter-status").value;

  const p = await api("/posts");

  let filtered = p;
  if (filterMonth) {
    filtered = filtered.filter((x) => {
      const dateStr = x.posted_at || x.created_at;
      if (!dateStr) return false;
      const d = new Date(dateStr);
      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const yyyymm = `${yyyy}-${mm}`;
      return yyyymm === filterMonth;
    });
  }
  if (filterDate) {
    filtered = filtered.filter((x) => {
      const dateStr = x.posted_at || x.created_at;
      if (!dateStr) return false;
      const d = new Date(dateStr);
      const yyyy = d.getFullYear();
      const mm = String(d.getMonth() + 1).padStart(2, '0');
      const dd = String(d.getDate()).padStart(2, '0');
      const yyyymmdd = `${yyyy}-${mm}-${dd}`;
      return yyyymmdd === filterDate;
    });
  }
  if (filterPlatform) {
    filtered = filtered.filter((x) => x.platform === filterPlatform);
  }
  if (filterStatus) {
    filtered = filtered.filter((x) => x.status === filterStatus);
  }

  $("#posts-table-wrap").innerHTML = `<table><tr><th>เวลา</th><th>Platform</th><th>วิธี</th><th>บัญชี</th><th>สถานะ</th><th>คอมเมนต์ลิงก์</th><th>ID</th></tr>
    ${filtered.map((x) => `<tr>
      <td class="muted">${x.posted_at ? new Date(x.posted_at).toLocaleString("th-TH") : "—"}</td>
      <td>${x.platform}</td>
      <td><span class="chip ${x.method}">${x.method}</span></td>
      <td class="muted">${esc(x.account)}</td>
      <td><span class="chip ${x.status}">${x.status}</span></td>
      <td>${x.comment_status ? `<span class="chip ${x.comment_status === "posted" ? "posted" : "failed"}">${x.comment_status}</span>` : "—"}</td>
      <td class="muted">${esc(x.external_id || x.error || "")}</td>
    </tr>`).join("") || '<tr><td colspan=7 class="muted">ไม่พบข้อมูลโพสต์ที่ตรงกับตัวกรอง</td></tr>'}</table>`;
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

// ---------------- report (P3)
async function renderReport() {
  const r = await api("/report/daily").catch(() => null);
  if (!r) { $("#tab-report").innerHTML = '<p class="muted">โหลดรายงานไม่ได้</p>'; return; }
  const wins = (r.ab_winners || []).map((w) =>
    `<tr><td>${esc(w.store)}</td><td>${w.platform}</td><td><b class="ok">${w.winner}</b></td><td>+${(w.lift * 100).toFixed(2)}%</td></tr>`).join("")
    || '<tr><td colspan="4" class="muted">ยังไม่มีผู้ชนะ A/B (เก็บ impression ไม่พอ)</td></tr>';
  $("#tab-report").innerHTML = `
    <div class="kpis" style="padding:0 0 14px">
      <div class="kpi"><div class="v">${r.stores_active}</div><div class="l">ร้าน active</div><div class="s bad">${r.stores_paused} หยุด</div></div>
      <div class="kpi"><div class="v">${r.posts_ok}</div><div class="l">โพสต์สำเร็จ</div><div class="s bad">${r.posts_failed} ล้มเหลว</div></div>
      <div class="kpi"><div class="v">${r.impressions.toLocaleString()}</div><div class="l">Impressions</div></div>
      <div class="kpi"><div class="v">${(r.ctr * 100).toFixed(2)}%</div><div class="l">CTR</div></div>
      <div class="kpi"><div class="v ok">฿${r.revenue_baht.toLocaleString()}</div><div class="l">รายได้ประเมิน</div></div>
      <div class="kpi"><div class="v">฿${r.content_cost_baht}</div><div class="l">ต้นทุน AI</div></div>
    </div>
    <div class="card"><h4>🏆 ผู้ชนะ A/B ต่อร้าน</h4>
      <table class="rep"><tr><th>ร้าน</th><th>ช่องทาง</th><th>ผู้ชนะ</th><th>ดีกว่า</th></tr>${wins}</table></div>`;
}

// ---------------- คลังวิดีโอ Google Flow
async function renderFlowVideos() {
  const el = $("#tab-flowvids");
  el.innerHTML = '<p class="muted">กำลังโหลดวิดีโอ Flow...</p>';
  const r = await api("/flow-videos").catch(() => null);
  if (!r) { el.innerHTML = '<p class="muted">โหลดวิดีโอ Flow ไม่ได้</p>'; return; }
  if (!r.count) {
    el.innerHTML = '<p class="muted">ยังไม่มีวิดีโอที่สร้างจาก Google Flow — รันบอทเพื่อสร้างคลิป</p>';
    return;
  }
  const cards = r.videos.map((v) => {
    const when = v.created_at ? new Date(v.created_at).toLocaleString("th-TH")
      : (v.mtime ? new Date(v.mtime * 1000).toLocaleString("th-TH") : "");
    const title = v.video_title || v.filename;
    const tag = v.platform ? ` <span class="chip posted">${v.platform}·${v.label || ""}</span>` : "";
    return `<div class="v">
      <video class="media" src="${getMediaUrl(v.media_url)}" muted loop playsinline controls preload="metadata"></video>
      <div class="meta"><b>${esc(title)}</b>${tag}</div>
      <div class="s dim">${v.store ? esc(v.store) + " · " : ""}${v.size_kb || 0} KB · ${when}</div>
      <div style="font-size:12px"><a href="${getMediaUrl(v.media_url)}" download>⬇️ ดาวน์โหลด</a></div>
    </div>`;
  }).join("");
  el.innerHTML = `<div class="s dim" style="padding:0 0 10px">คลังวิดีโอจาก Google Flow ทั้งหมด ${r.count} คลิป (เก็บในเครื่อง)</div>
    <div class="preview">${cards}</div>`;
}

// ---------------- 🧠 การเรียนรู้ (self-improvement insights)
async function renderInsights() {
  const el = $("#tab-insights");
  el.innerHTML = '<p class="muted">กำลังโหลดสมองของบอท...</p>';
  const d = await api("/insights").catch(() => null);
  if (!d) { el.innerHTML = '<p class="muted">โหลด insights ไม่ได้</p>'; return; }
  const mode = d.metric_mode === "eng_rate" ? "Engagement-rate" : "CTR";
  const rkey = d.metric_mode === "eng_rate" ? "eng_rate" : "ctr";
  const updated = d.updated_at ? new Date(d.updated_at).toLocaleString("th-TH") : "—";
  if (!d.ready) {
    el.innerHTML = `<div class="card"><h4>🧠 บอทยังเก็บข้อมูลอยู่</h4>
      <p class="muted">ยังมีผลไม่พอจะสรุป (ต้องสะสม impression ให้มากพอต่อกลุ่ม)<br>
      impressions สะสม: <b>${(d.total_impressions || 0).toLocaleString()}</b> · อัปเดตล่าสุด: ${updated}</p>
      <p class="muted">พอวิวสะสมมากขึ้น บอทจะเริ่มสรุปว่า ภาษา/รูปแบบ/แพลตฟอร์มไหนปังที่สุด แล้วเอาไปปรับการเขียนเอง</p></div>`;
    return;
  }
  const NAME = { food: "🍜", thai: "🇹🇭 ไทย", english: "🇬🇧 อังกฤษ", isaan: "🪕 อีสาน", unknown: "ไม่ระบุ" };
  const rows = (obj) => Object.entries(obj || {}).map(([k, v], i) =>
    `<tr><td>${i === 0 ? "🏆 " : ""}${NAME[k] || k}</td><td><b>${(v[rkey] * 100).toFixed(2)}%</b></td>
     <td class="muted">${v.impressions.toLocaleString()} imp · ${v.engagement} eng</td></tr>`).join("") ||
    '<tr><td colspan="3" class="muted">ข้อมูลยังไม่พอ (ต้อง ≥2 กลุ่ม)</td></tr>';
  const tbl = (title, obj) => `<div class="card"><h4>${title}</h4>
    <table class="rep" style="width:100%"><tr><th>กลุ่ม</th><th>${mode}</th><th></th></tr>${rows(obj)}</table></div>`;
  const hooks = (d.top_hooks || []).filter(h => h.hook).slice(0, 6).map(h =>
    `<li>${(h.rate * 100).toFixed(2)}% <span class="muted">[${h.platform}/${h.label}]</span> "${esc(h.hook)}"</li>`).join("");
  el.innerHTML = `
    <div class="kpis" style="padding:0 0 14px">
      <div class="kpi"><div class="v ok">${(d.baseline_eng_rate * 100).toFixed(2)}%</div><div class="l">Engagement-rate ฐาน</div></div>
      <div class="kpi"><div class="v">${(d.total_impressions || 0).toLocaleString()}</div><div class="l">Impressions สะสม</div></div>
      <div class="kpi"><div class="v">${mode}</div><div class="l">วัดผลด้วย</div></div>
    </div>
    <div class="s dim" style="padding:0 0 10px">บอทใช้ข้อมูลนี้ปรับการเขียนคอนเทนต์อัตโนมัติ · อัปเดตล่าสุด ${updated}</div>
    <div class="grid">
      ${tbl("🗣️ ภาษาบทพูดที่ปัง", d.by_spoken_lang)}
      ${tbl("🅰️🅱️ รูปแบบ A vs B", d.by_label)}
      ${tbl("📱 แพลตฟอร์ม", d.by_platform)}
    </div>
    <div class="card"><h4>🔥 Hook ที่พิสูจน์แล้วว่าปัง</h4>
      <ul style="margin:0;padding-left:18px;line-height:1.8">${hooks || '<li class="muted">ยังไม่มี</li>'}</ul></div>`;
}

// ---------------- driver
function render(tab) {
  ({ stores: renderStores, content: renderContent, posts: renderPosts,
     platform: renderPlatform, report: renderReport, flow: renderFlow,
     flowvids: renderFlowVideos, insights: renderInsights }[tab] || (() => {}))();
}
let liveStarted = false;
function startLiveUpdates() {
  if (liveStarted) return;
  liveStarted = true;
  startProgress();
  setInterval(loadKpis, 15000);
}
async function loadAll() {
  const isLocal = location.hostname === "localhost" || location.hostname === "127.0.0.1" || location.hostname.startsWith("192.168.");
  if (!isLocal && !backendUrl) {
    // เปิดผ่าน Funnel/โดเมนเดียวกับ backend → ลอง API ที่ origin เดียวกันก่อน ถ้าได้ใช้เลยไม่ต้องกดเชื่อม
    try { await api("/keys/status"); }
    catch (e) { loadBanner().catch(() => {}); return; }  // ไม่มี backend ที่ origin นี้ (เช่น Vercel) → ขึ้นปุ่มเชื่อม
  }
  await Promise.all([loadSystem().catch(() => {}), loadBanner().catch(() => {}), loadKpis().catch((e) => toast(e.message, true))]);
  const active = document.querySelector(".tabs button.active").dataset.tab;
  render(active);
  startLiveUpdates();
}

// (ลบฟีเจอร์ "เชื่อมต่อ API" ออกแล้ว — ใช้ origin เดียวกับ backend ผ่าน Funnel/local)

// Register filter event listeners
$("#content-filter-month").addEventListener("change", renderContent);
$("#content-filter-platform").addEventListener("change", renderContent);
$("#btn-content-filter-clear").addEventListener("click", () => {
  $("#content-filter-month").value = "";
  $("#content-filter-platform").value = "";
  renderContent();
});

$("#posts-filter-month").addEventListener("change", () => {
  $("#posts-filter-date").value = "";
  renderPosts();
});
$("#posts-filter-date").addEventListener("change", () => {
  $("#posts-filter-month").value = "";
  renderPosts();
});
$("#posts-filter-platform").addEventListener("change", renderPosts);
$("#posts-filter-status").addEventListener("change", renderPosts);
$("#btn-posts-filter-clear").addEventListener("click", () => {
  $("#posts-filter-month").value = "";
  $("#posts-filter-date").value = "";
  $("#posts-filter-platform").value = "";
  $("#posts-filter-status").value = "";
  renderPosts();
});

loadAll();   // เชื่อม backend ได้ (local / Funnel / ตั้ง URL เอง) → loadAll เริ่ม live updates ให้เอง

// ===== Modal helpers =====
function showModal(title, html) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = html;
  document.getElementById('modal').classList.remove('hidden');
}
function closeModal() {
  document.getElementById('modal').classList.add('hidden');
}
document.getElementById('modal').addEventListener('click', (e) => {
  if (e.target.dataset.close !== undefined) closeModal();
});
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') closeModal();
});

// ===== Scrape button =====
document.getElementById('btn-scrape').onclick = async () => {
  try {
    toast('????????????????? Shopee...');
    const r = await api('/scrape', { method: 'POST' });
    showModal('??????????????',
      '<p>?????? <b>' + (r.fetched||0) + '</b> ?????? &nbsp;|&nbsp; ????????? <b class=\"ok\">' + (r.added||0) + '</b> &nbsp;|&nbsp; ???? <b class=\"dim\">' + (r.skipped||0) + '</b></p>'
    );
    loadAll();
  } catch(e) { toast(e.message, true); }
};

// ===== Open Chrome button =====
const btnOpenChrome = document.getElementById('btn-open-chrome');
if (btnOpenChrome) {
  btnOpenChrome.onclick = async () => {
    try {
      toast("กำลังส่งคำสั่งเปิด Google Flow...");
      const r = await api("/chrome/open", { method: "POST" });
      toast(r.message || "เปิดเบราว์เซอร์บอทแล้ว");
    } catch (e) {
      toast(e.message, true);
    }
  };
}
