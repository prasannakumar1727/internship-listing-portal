/* Internship Listing Portal - frontend logic (calls the Flask REST API) */
const API = (window.API_BASE || "").replace(/\/$/, "");
const $ = (s, r = document) => r.querySelector(s);
const qs = new URLSearchParams(location.search);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const money = (n) => (n > 0 ? "₹" + Number(n).toLocaleString("en-IN") + "/month" : "Unpaid");
const months = (n) => n + " month" + (n > 1 ? "s" : "");
const lines = (t) => String(t || "").split("\n").filter(Boolean).map((x) => `<li>${esc(x)}</li>`).join("");

async function api(path, opts) {
  try {
    const r = await fetch(API + path, opts);
    let data = null;
    try { data = await r.json(); } catch (_) {}
    return { ok: r.ok, status: r.status, data: data || {} };
  } catch (_) {
    return { ok: false, status: 0, data: { error: "Cannot reach the server. Please make sure the backend is running." } };
  }
}

function shell() {
  document.body.insertAdjacentHTML("afterbegin",
    `<header class="site-header"><div><a class="logo" href="index.html">Internship Portal</a>
     <nav><a href="index.html">Browse</a><a href="admin.html">Admin</a></nav></div></header>`);
}

/* ---------- listing page ---------- */
async function initList() {
  const ids = ["search", "location", "domain", "duration", "work_mode", "min_stipend", "sort"];
  let page = 1, reqId = 0, timer;
  const f = await api("/filters");
  if (f.ok) {
    f.data.locations.forEach((v) => $("#location").add(new Option(v, v)));
    f.data.domains.forEach((v) => $("#domain").add(new Option(v, v)));
    f.data.durations.forEach((v) => $("#duration").add(new Option(months(v), v)));
  }
  const card = (i) => `<article class="card">
    <div class="tags"><span class="tag">${esc(i.domain)}</span><span class="tag mode">${esc(i.work_mode)}</span>${i.expired ? '<span class="tag exp">Closed</span>' : ""}</div>
    <h3><a href="internship.html?id=${i.id}">${esc(i.title)}</a></h3><p class="company">${esc(i.company)}</p>
    <ul class="meta"><li><b>Location:</b> ${esc(i.location)}</li><li><b>Duration:</b> ${months(i.duration_months)}</li>
    <li><b>Stipend:</b> ${money(i.stipend)}</li><li><b>Apply by:</b> ${esc(i.deadline)}</li></ul>
    <a class="btn" href="internship.html?id=${i.id}">View details</a></article>`;

  async function load() {
    const id = ++reqId;
    const p = new URLSearchParams({ page, per_page: 9 });
    ids.forEach((k) => { const v = $("#" + k).value.trim(); if (v) p.set(k, v); });
    if ($("#sort").value === "newest") p.delete("sort");
    $("#count").textContent = "Loading…";
    const r = await api("/internships?" + p);
    if (id !== reqId) return; // ignore stale responses
    if (!r.ok) { $("#grid").innerHTML = `<div class="empty">${esc(r.data.error || "Something went wrong.")}</div>`; $("#count").textContent = ""; $("#pager").innerHTML = ""; return; }
    const d = r.data;
    $("#count").textContent = d.total === 1 ? "1 internship found" : d.total + " internships found";
    $("#grid").innerHTML = d.items.length ? d.items.map(card).join("") : '<div class="empty">No internships found. Try different keywords or clear the filters.</div>';
    $("#pager").innerHTML = d.pages > 1 ? `<button class="btn secondary" id="prev" ${d.page <= 1 ? "disabled" : ""}>Previous</button><span>Page ${d.page} of ${d.pages}</span><button class="btn secondary" id="next" ${d.page >= d.pages ? "disabled" : ""}>Next</button>` : "";
    if ($("#prev")) $("#prev").onclick = () => { page--; load(); scrollTo(0, 0); };
    if ($("#next")) $("#next").onclick = () => { page++; load(); scrollTo(0, 0); };
  }
  const reset = () => { page = 1; load(); };
  $("#search").addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(reset, 300); });
  ids.slice(1).forEach((k) => $("#" + k).addEventListener("change", reset));
  $("#filters").addEventListener("submit", (e) => { e.preventDefault(); reset(); });
  $("#clear").onclick = () => { ids.forEach((k) => ($("#" + k).value = k === "sort" ? "newest" : "")); reset(); };
  load();
}

/* ---------- detail page ---------- */
async function initDetail() {
  const box = $("#detail");
  const r = await api("/internships/" + encodeURIComponent(qs.get("id") || "0"));
  if (!r.ok) {
    box.innerHTML = `<div class="card center"><h2>${r.status === 404 ? "Internship not found" : "Something went wrong"}</h2><p>${esc(r.status === 404 ? "The internship you are looking for does not exist or was removed." : r.data.error)}</p><a class="btn" href="index.html">Back to all internships</a></div>`;
    return;
  }
  const i = r.data;
  document.title = i.title + " - " + i.company;
  box.innerHTML = `<div class="detail"><a href="index.html">&larr; All internships</a>
    <h1>${esc(i.title)}</h1><p class="company">${esc(i.company)}</p>
    <div class="tags"><span class="tag">${esc(i.domain)}</span><span class="tag mode">${esc(i.work_mode)}</span></div>
    <section><ul class="meta"><li><b>Location:</b> ${esc(i.location)}</li><li><b>Duration:</b> ${months(i.duration_months)}</li><li><b>Stipend:</b> ${money(i.stipend)}</li><li><b>Deadline:</b> ${esc(i.deadline)}${i.expired ? " (closed)" : ""}</li></ul></section>
    <section><h2>Description</h2><p>${esc(i.description)}</p></section>
    <section><h2>Requirements</h2><ul>${lines(i.requirements)}</ul></section>
    <section><h2>Benefits</h2><ul>${lines(i.benefits)}</ul></section>
    ${i.expired ? '<span class="btn disabled" aria-disabled="true">Applications closed</span>' : `<a class="btn" href="apply.html?id=${i.id}">Apply Now</a>`}</div>`;
}

/* ---------- application form ---------- */
const EMAIL = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$/;
function clientValidate(v, file) {
  const e = {};
  const phone = v.phone.replace(/[\s\-()]/g, "").replace(/^(\+91|91|0)(?=\d{10}$)/, "");
  if (!v.name.trim()) e.name = "Name is required."; else if (v.name.trim().length < 2) e.name = "Name must be at least 2 characters.";
  if (!v.email.trim()) e.email = "Email is required."; else if (!EMAIL.test(v.email.trim())) e.email = "Enter a valid email address (e.g. name@example.com).";
  if (!phone) e.phone = "Phone number is required."; else if (!/^[6-9]\d{9}$/.test(phone)) e.phone = "Enter a valid 10-digit mobile number.";
  if (v.resume_link.trim() && !/^https?:\/\/\S+\.\S+/i.test(v.resume_link.trim())) e.resume_link = "Enter a valid link starting with http:// or https://.";
  if (file) {
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["pdf", "docx"].includes(ext)) e.resume_file = "Only PDF or DOCX files are allowed.";
    else if (file.size > 5 * 1024 * 1024) e.resume_file = "File is too large (max 5 MB).";
  }
  if (!v.resume_link.trim() && !file && !e.resume_link) e.resume_link = "Provide a resume link or upload a PDF/DOCX file.";
  if (v.cover_note.length > 500) e.cover_note = "Cover note must be 500 characters or fewer.";
  return e;
}

async function initApply() {
  const id = qs.get("id");
  const r = await api("/internships/" + encodeURIComponent(id || "0"));
  const banner = $("#banner"), form = $("#form");
  const show = (msg) => { banner.textContent = msg; banner.hidden = false; };
  if (!r.ok) { form.hidden = true; show(r.status === 404 ? "Internship not found." : r.data.error); return; }
  $("#target").textContent = r.data.title + " at " + r.data.company;
  if (r.data.expired) { form.hidden = true; show("The application deadline for this internship has passed."); return; }

  const showErrors = (errs) => {
    document.querySelectorAll(".err").forEach((s) => { s.textContent = errs[s.dataset.for] || ""; s.parentElement.classList.toggle("invalid", !!errs[s.dataset.for]); });
    const first = Object.keys(errs).find((k) => $("#" + k));
    if (first) $("#" + first).focus();
  };
  form.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    banner.hidden = true;
    const v = Object.fromEntries(["name", "email", "phone", "resume_link", "cover_note"].map((k) => [k, $("#" + k).value]));
    const file = $("#resume_file").files[0] || null;
    const errs = clientValidate(v, file);
    showErrors(errs);
    if (Object.keys(errs).length) return;
    const btn = $("#submit");
    btn.disabled = true; btn.textContent = "Submitting…";
    const fd = new FormData(form); fd.append("internship_id", id);
    const res = await api("/applications", { method: "POST", body: fd });
    if (res.status === 201) {
      location.href = `success.html?app=${res.data.application_id}&title=${encodeURIComponent(r.data.title)}&company=${encodeURIComponent(r.data.company)}`;
      return;
    }
    btn.disabled = false; btn.textContent = "Submit application";
    if (res.data.errors) showErrors(res.data.errors);
    show(res.data.error || "Could not submit the application.");
  });
}

function initSuccess() {
  const app = qs.get("app");
  $("#msg").innerHTML = app
    ? `<p class="big">Application submitted!</p><p>Your application ID is <b>#${esc(app)}</b>.</p><p>${esc(qs.get("title") || "")} ${qs.get("company") ? "at " + esc(qs.get("company")) : ""}</p><p>Status: Received</p><a class="btn" href="index.html">Browse more internships</a>`
    : `<p>No application found.</p><a class="btn" href="index.html">Browse internships</a>`;
}

/* ---------- admin ---------- */
function initAdmin() {
  const key = $("#key"), msg = $("#adminmsg");
  key.value = sessionStorage.getItem("adminKey") || "";
  const say = (t, ok) => { msg.textContent = t; msg.className = "banner" + (ok ? " ok" : ""); msg.hidden = !t; };
  const headers = () => ({ "X-Admin-Key": key.value });
  async function load() {
    sessionStorage.setItem("adminKey", key.value);
    const r = await api("/applications", { headers: headers() });
    if (!r.ok) { say(r.data.error || "Failed to load.", false); return; }
    say("", true);
    $("#apps tbody").innerHTML = r.data.items.map((a) => `<tr><td>#${a.id}</td><td>${esc(a.internship_title)}<br><small>${esc(a.company)}</small></td><td>${esc(a.name)}</td><td>${esc(a.email)}</td><td>${esc(a.phone)}</td>
      <td>${a.resume_link ? `<a href="${esc(a.resume_link)}" target="_blank" rel="noopener noreferrer">Link</a>` : ""} ${a.resume_file ? `<a href="${API}/applications/${a.id}/resume?key=${encodeURIComponent(key.value)}">File</a>` : ""}</td>
      <td>${esc(a.applied_date)}</td><td><select data-id="${a.id}">${["Received", "Shortlisted", "Rejected"].map((s) => `<option ${s === a.status ? "selected" : ""}>${s}</option>`).join("")}</select></td></tr>`).join("") || '<tr><td colspan="8">No applications yet.</td></tr>';
  }
  $("#load").onclick = load;
  $("#apps").addEventListener("change", async (e) => {
    if (!e.target.dataset.id) return;
    const r = await api("/applications/" + e.target.dataset.id, { method: "PATCH", headers: { ...headers(), "Content-Type": "application/json" }, body: JSON.stringify({ status: e.target.value }) });
    say(r.ok ? "Status updated." : r.data.error, r.ok);
  });
  $("#addform").addEventListener("submit", async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(new FormData(e.target));
    const r = await api("/internships", { method: "POST", headers: { ...headers(), "Content-Type": "application/json" }, body: JSON.stringify(body) });
    say(r.ok ? "Internship added (id " + r.data.id + ")." : (r.data.errors ? Object.entries(r.data.errors).map(([k, v]) => k + ": " + v).join("; ") : r.data.error), r.ok);
    if (r.ok) e.target.reset();
  });
  if (key.value) load();
}

shell();
({ list: initList, detail: initDetail, apply: initApply, success: initSuccess, admin: initAdmin })[document.body.dataset.page]?.();
