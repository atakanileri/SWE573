// The page is plain HTML. Every list, save, login and counter click goes to
// the FastAPI app on this same origin (see /docs). The login token is kept in
// localStorage and sent as "Authorization: Bearer ...".

const TOKEN_KEY = "ica_token";

let token = localStorage.getItem(TOKEN_KEY);
let me = null;
let crafts = [];
let categories = [];
let tags = [];
let chip = "All";
let view = "home";
let editingId = null;
let selectedCategory = "";
let selectedTags = [];
let current = null;
let searchTimer = null;

function $(id) {
  return document.getElementById(id);
}

function esc(value) {
  return String(value == null ? "" : value).replace(/[&<>"']/g, function (ch) {
    return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch];
  });
}

function errorText(data) {
  if (!data || data.detail == null) return "Something went wrong.";
  const detail = data.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map(function (item) {
        if (typeof item === "string") return item;
        if (item && item.msg) return item.msg;
        return "";
      })
      .filter(Boolean)
      .join(" ");
  }
  return "Something went wrong.";
}

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.className = "toast show";
  clearTimeout(el._t);
  el._t = setTimeout(function () {
    el.className = "toast";
  }, 2600);
}

async function api(method, path, body) {
  const opts = { method: method, headers: {} };
  if (token) opts.headers.Authorization = "Bearer " + token;
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, opts);
  } catch (err) {
    return { ok: false, status: 0, data: { detail: "Could not reach the API." } };
  }
  let data = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (err) {
      data = { detail: text };
    }
  }
  const result = { ok: response.ok, status: response.status, data: data };
  const isAuthAttempt = path === "/api/auth/login" || path === "/api/auth/register";
  if (response.status === 401 && token && !isAuthAttempt) {
    clearSession();
    showLanding("Your session ended. Please log in again.");
    result.loggedOut = true;
  }
  return result;
}

function setCounter(n) {
  $("counterVal").textContent = n;
  $("landingCounterVal").textContent = n;
}

async function refreshCounter() {
  const res = await api("GET", "/api/counter");
  if (res.ok) setCounter(res.data.count);
}

async function bumpCounter() {
  const res = await api("POST", "/api/counter");
  if (res.ok) setCounter(res.data.count);
  else if (!res.loggedOut) toast(errorText(res.data));
}

function clearSession() {
  token = null;
  me = null;
  localStorage.removeItem(TOKEN_KEY);
}

function saveSession(data) {
  token = data.token;
  me = data.user;
  localStorage.setItem(TOKEN_KEY, token);
}

function show(which) {
  $("vHome").className = which === "home" ? "" : "hide";
  $("vForm").className = which === "form" ? "" : "hide";
  $("vLanding").className = which === "landing" ? "" : "hide";
  $("hdr").className = which === "landing" ? "hide" : "";
  window.scrollTo(0, 0);
}

function showLanding(message) {
  show("landing");
  const err = $("landingError");
  if (message) {
    err.textContent = message;
    err.classList.remove("hide");
  } else {
    err.textContent = "";
    err.classList.add("hide");
  }
}

function setAuthMode(registering) {
  $("loginForm").className = registering ? "hide" : "";
  $("registerForm").className = registering ? "" : "hide";
  $("showRegister").textContent = registering ? "Back to log in" : "Register";
  $("landingError").classList.add("hide");
}

async function enterApp() {
  $("userBtn").textContent = me.display_name + " ▾";
  show("home");
  view = "home";
  chip = "All";
  $("q").value = "";
  await loadMeta();
  renderChips();
  await loadCrafts();
  refreshDraftCount();
}

async function loadMeta() {
  const cats = await api("GET", "/api/categories");
  const tagRes = await api("GET", "/api/tags");
  if (cats.ok) categories = cats.data;
  if (tagRes.ok) tags = tagRes.data;
}

function renderChips() {
  const names = ["All"].concat(categories).concat(tags.map(function (t) { return "#" + t; }));
  $("chips").innerHTML = names
    .map(function (name) {
      const on = name === chip ? " on" : "";
      return '<button type="button" class="chip' + on + '" data-chip="' + esc(name) + '">' + esc(name) + "</button>";
    })
    .join("");
}

function craftsUrl() {
  const params = new URLSearchParams();
  if (view === "mine") params.set("mine", "true");
  else if (view === "drafts") {
    params.set("mine", "true");
    params.set("status", "draft");
  } else if (view === "favs") params.set("favorites", "true");
  else {
    const q = $("q").value.trim();
    if (q) params.set("q", q);
    if (chip !== "All") {
      if (chip.charAt(0) === "#") params.set("tag", chip.slice(1));
      else params.set("category", chip);
    }
  }
  const query = params.toString();
  return "/api/crafts" + (query ? "?" + query : "");
}

function sectionTitle() {
  if (view === "mine") return "My posts";
  if (view === "drafts") return "My drafts";
  if (view === "favs") return "Favorites";
  return "";
}

async function loadCrafts() {
  $("filters").className = "top" + (view === "home" ? "" : " hide");
  const title = sectionTitle();
  $("secTitle").textContent = title;
  $("secTitle").className = "sec" + (title ? "" : " hide");
  $("nBrowse").className = "navlink" + (view === "home" ? " cur" : "");
  $("grid").innerHTML = '<div class="empty">Loading…</div>';
  const res = await api("GET", craftsUrl());
  if (!res.ok) {
    if (!res.loggedOut) $("grid").innerHTML = '<div class="empty">' + esc(errorText(res.data)) + "</div>";
    return;
  }
  crafts = res.data;
  renderGrid();
}

function photoHtml(craft, tall) {
  const height = tall ? Math.max((craft.card_height || 240) + 80, 360) : craft.card_height || 220;
  const alt = esc(craft.title) + (tall ? " — photo" : "");
  let img = "";
  if (craft.image_url && /^https?:\/\//i.test(craft.image_url)) {
    img = '<img alt="' + alt + '" src="' + esc(craft.image_url) + '">';
  }
  return (
    '<div class="ph" style="height:' + height + 'px">' +
    img +
    '<div class="ic">▧</div><div class="pn">' + esc(craft.title) + (tall ? " — photo" : "") + "</div></div>"
  );
}

function renderGrid() {
  if (!crafts.length) {
    $("grid").innerHTML = '<div class="empty">Nothing here yet.</div>';
    return;
  }
  $("grid").innerHTML = crafts
    .map(function (craft) {
      const heart = craft.status === "draft"
        ? ""
        : '<button type="button" class="heart' + (craft.favorited ? " on" : "") + '" data-fav="' + craft.id + '" aria-label="Favorite">' +
          (craft.favorited ? "♥" : "♡") + "</button>";
      const badge = craft.status === "draft" ? '<span class="badge">Draft · only you can see this</span>' : "";
      return (
        '<div class="card" tabindex="0" role="link" data-id="' + craft.id + '">' +
        photoHtml(craft, false) +
        '<div class="cb"><div class="ct">' + esc(craft.title) + "</div>" +
        '<div class="loc"><i class="pin"></i>' + esc(craft.location_text || "Location not set") + "</div>" +
        badge + heart + "</div></div>"
      );
    })
    .join("");
}

function pinStyle(lat, lng) {
  if (lat == null || lng == null || lat === "" || lng === "") return "left:50%;top:42%";
  const left = 18 + ((Number(lng) + 180) / 360) * 64;
  const top = 18 + ((70 - Number(lat)) / 130) * 64;
  return "left:" + left.toFixed(1) + "%;top:" + top.toFixed(1) + "%";
}

function fillDetail(craft, preview) {
  current = craft;
  const tags = (craft.tags || [])
    .map(function (tag) { return '<span class="tag">#' + esc(tag) + "</span>"; })
    .join("");
  let actions = "";
  if (preview) {
    actions = '<span class="hint">Preview — this is not saved yet.</span>';
  } else if (craft.status !== "draft") {
    actions =
      '<button type="button" class="b' + (craft.favorited ? " on" : "") + '" id="detFav">' +
      (craft.favorited ? "♥ Favorited" : "♡ Favorite") + "</button>" +
      '<button type="button" class="b" id="detRep">⚑ Report</button>';
  }
  if (!preview && craft.owner) {
    actions += '<button type="button" class="b" id="detEdit">Edit</button>' +
      '<button type="button" class="b" id="detDelete">Delete</button>';
  }
  const description = craft.description
    ? '<div class="para"><b>Description</b>' + esc(craft.description) + "</div>"
    : "";
  const note = craft.note
    ? '<div class="para"><b>Note from the poster</b>' + esc(craft.note) + "</div>"
    : "";
  $("det").innerHTML =
    '<button type="button" class="x" id="closeDet" aria-label="Close">×</button>' +
    '<div class="det">' + photoHtml(craft, true) +
    '<div class="info"><h1>' + esc(craft.title) + "</h1>" +
    '<div class="by">Posted by ' + esc(craft.author_name || (me && me.display_name) || "") + "</div>" +
    '<div class="kv"><b>Category</b>' + esc(craft.category || "—") + "</div>" +
    '<div class="kv"><b>Tags</b>' + (tags || "—") + "</div>" +
    description +
    '<div class="kv"><b>Dimensions</b>' + esc(craft.dimensions || "—") + "</div>" +
    '<div class="kv"><b>Colors</b>' + esc(craft.colors || "—") + "</div>" +
    '<div class="kv"><b>Tools</b>' + esc(craft.tools || "—") + "</div>" +
    '<div class="para"><b>Backstory</b>' + esc(craft.backstory || "—") + "</div>" +
    note +
    '<div class="mini"><div class="mpin" style="' + pinStyle(craft.latitude, craft.longitude) + '"></div>' +
    '<div class="mlbl">' + esc(craft.location_text || "Location not set") + "</div></div>" +
    '<div style="margin-top:16px">' + actions + "</div></div></div>";
  $("ovDet").classList.add("open");
  const close = $("closeDet");
  if (close) close.addEventListener("click", function () { closeOv("ovDet"); });
  const fav = $("detFav");
  if (fav) fav.addEventListener("click", function () { toggleFav(craft.id); });
  const rep = $("detRep");
  if (rep) rep.addEventListener("click", openReport);
  const edit = $("detEdit");
  if (edit) edit.addEventListener("click", function () { closeOv("ovDet"); openForm(craft); });
  const del = $("detDelete");
  if (del) del.addEventListener("click", function () { deleteCraft(craft); });
}

async function openDetail(id) {
  const res = await api("GET", "/api/crafts/" + id);
  if (!res.ok) {
    if (!res.loggedOut) toast(errorText(res.data));
    return;
  }
  fillDetail(res.data, false);
}

function closeOv(id) {
  $(id).classList.remove("open");
}

function openReport() {
  $("repText").value = "";
  $("ovRep").classList.add("open");
}

async function submitReport() {
  if (!current) return;
  const details = $("repText").value.trim();
  if (details.length < 3) {
    toast("Please write what is wrong with this post.");
    return;
  }
  const res = await api("POST", "/api/crafts/" + current.id + "/reports", {
    reason: $("repReason").value,
    details: details,
  });
  if (!res.ok) {
    if (!res.loggedOut) toast(errorText(res.data));
    return;
  }
  closeOv("ovRep");
  toast("Thanks, an admin will review it.");
}

async function toggleFav(id) {
  const res = await api("POST", "/api/crafts/" + id + "/favorite");
  if (!res.ok) {
    if (!res.loggedOut) toast(errorText(res.data));
    return;
  }
  const inList = crafts.find(function (craft) { return craft.id === id; });
  if (inList) inList.favorited = res.data.favorited;
  if (current && current.id === id) current.favorited = res.data.favorited;
  if (view === "favs") await loadCrafts();
  else renderGrid();
  if (current && current.id === id && $("ovDet").classList.contains("open")) fillDetail(current, false);
}

async function deleteCraft(craft) {
  if (!confirm("Delete “" + craft.title + "”? This can't be undone.")) return;
  const res = await api("DELETE", "/api/crafts/" + craft.id);
  if (!res.ok) {
    if (!res.loggedOut) toast(errorText(res.data));
    return;
  }
  closeOv("ovDet");
  toast("Post deleted.");
  await loadCrafts();
  refreshDraftCount();
}

async function refreshDraftCount() {
  const res = await api("GET", "/api/crafts?mine=true&status=draft");
  if (res.ok) $("dcnt").textContent = res.data.length ? String(res.data.length) : "";
}

function go(next) {
  view = next;
  show("home");
  loadCrafts();
}

function renderSelectors() {
  $("catSel").innerHTML = categories
    .map(function (name) {
      const on = name === selectedCategory ? " on" : "";
      return '<button type="button" class="chip' + on + '" data-cat="' + esc(name) + '">' + esc(name) + "</button>";
    })
    .join("");
  $("tagSel").innerHTML = tags
    .map(function (name) {
      const on = selectedTags.indexOf(name) >= 0 ? " on" : "";
      return '<button type="button" class="chip' + on + '" data-tag="' + esc(name) + '">#' + esc(name) + "</button>";
    })
    .join("");
}

function setField(id, value) {
  $(id).value = value || "";
}

async function openForm(craft) {
  if (!categories.length) await loadMeta();
  document.querySelectorAll("#vForm .f").forEach(function (field) { field.classList.remove("err"); });
  $("formErrors").className = "form-errors hide";
  $("formErrors").textContent = "";
  if (craft) {
    editingId = craft.id;
    selectedCategory = craft.category || "";
    selectedTags = (craft.tags || []).slice();
    setField("iTitle", craft.title);
    setField("iDesc", craft.description);
    setField("iPhoto", craft.image_url);
    setField("iDim", craft.dimensions);
    setField("iCol", craft.colors);
    setField("iTools", craft.tools);
    setField("iBack", craft.backstory);
    setField("iCustom", craft.note);
    setField("iLoc", craft.location_text);
    setField("iLat", craft.latitude == null ? "" : craft.latitude);
    setField("iLng", craft.longitude == null ? "" : craft.longitude);
    $("formHeading").textContent = craft.status === "draft" ? "Edit draft" : "Edit craft";
    $("draftNote").textContent = craft.status === "draft" ? "Editing a draft" : "Editing your post";
    placePin(!!craft.location_text);
  } else {
    editingId = null;
    selectedCategory = "";
    selectedTags = [];
    ["iTitle", "iDesc", "iPhoto", "iDim", "iCol", "iTools", "iBack", "iCustom", "iLoc", "iLat", "iLng"].forEach(function (id) {
      $(id).value = "";
    });
    $("formHeading").textContent = "New Craft Post";
    $("draftNote").textContent = "Not saved yet";
    placePin(false);
  }
  renderSelectors();
  show("form");
  $("nBrowse").className = "navlink";
}

function placePin(on) {
  $("fPin").className = on ? "mpin" : "mpin ghost";
  $("fLocLbl").textContent = on
    ? ($("iLoc").value || "Pin placed")
    : "Click the map to place a sample pin (Toros, Mersin)";
}

function numOrNull(raw) {
  if (raw.trim() === "") return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : NaN;
}

function readForm(status) {
  const lat = numOrNull($("iLat").value);
  const lng = numOrNull($("iLng").value);
  return {
    title: $("iTitle").value.trim(),
    description: $("iDesc").value.trim(),
    image_url: $("iPhoto").value.trim(),
    category: selectedCategory,
    tags: selectedTags.slice(),
    dimensions: $("iDim").value.trim(),
    colors: $("iCol").value.trim(),
    tools: $("iTools").value.trim(),
    backstory: $("iBack").value.trim(),
    note: $("iCustom").value.trim(),
    location_text: $("iLoc").value.trim(),
    latitude: lat,
    longitude: lng,
    status: status,
  };
}

function highlight(status, body) {
  const publish = status === "published";
  const checks = [
    ["fTitle", !!body.title],
    ["fDesc", !publish || !!body.description],
    ["fPhotos", !body.image_url || /^https?:\/\//i.test(body.image_url)],
    ["fCat", !publish || !!body.category],
    ["fTags", !publish || body.tags.length > 0],
    ["fDim", !publish || !!body.dimensions],
    ["fCol", !publish || !!body.colors],
    ["fTools", !publish || !!body.tools],
    ["fBack", !publish || !!body.backstory],
    ["fLoc", !publish || !!body.location_text],
  ];
  let ok = true;
  checks.forEach(function (pair) {
    const bad = !pair[1];
    $(pair[0]).classList.toggle("err", bad);
    if (bad) ok = false;
  });
  if (Number.isNaN(body.latitude) || Number.isNaN(body.longitude)) {
    ok = false;
    showFormErrors("Latitude and longitude need to be numbers, or left empty.");
  }
  return ok;
}

function showFormErrors(message) {
  const box = $("formErrors");
  box.textContent = message;
  box.classList.remove("hide");
}

async function save(status) {
  const body = readForm(status);
  if (Number.isNaN(body.latitude) || Number.isNaN(body.longitude)) {
    showFormErrors("Latitude and longitude need to be numbers, or left empty.");
    return;
  }
  if (!highlight(status, body)) {
    const bad = document.querySelector("#vForm .f.err");
    if (bad) bad.scrollIntoView({ block: "center" });
    toast(status === "draft" ? "A draft still needs a title." : "Please fix the highlighted fields.");
    return;
  }

  const path = editingId ? "/api/crafts/" + editingId : "/api/crafts";
  const method = editingId ? "PUT" : "POST";
  const res = await api(method, path, body);
  if (!res.ok) {
    if (!res.loggedOut) {
      showFormErrors(errorText(res.data));
      toast("The server rejected the post.");
    }
    return;
  }
  $("formErrors").classList.add("hide");
  if (status === "draft") {
    editingId = res.data.id;
    $("draftNote").textContent = "Saved as draft just now";
    $("formHeading").textContent = "Edit draft";
    toast("Draft saved — find it under your name, My drafts.");
    refreshDraftCount();
    return;
  }
  chip = "All";
  $("q").value = "";
  renderChips();
  toast("Your craft is published!");
  go("home");
  refreshDraftCount();
}

function preview() {
  const body = readForm("published");
  if (Number.isNaN(body.latitude)) body.latitude = null;
  if (Number.isNaN(body.longitude)) body.longitude = null;
  fillDetail(
    {
      title: body.title || "Untitled",
      description: body.description,
      image_url: body.image_url,
      category: body.category,
      tags: body.tags,
      dimensions: body.dimensions,
      colors: body.colors,
      tools: body.tools,
      backstory: body.backstory,
      note: body.note,
      location_text: body.location_text,
      latitude: body.latitude,
      longitude: body.longitude,
      card_height: 260,
      author_name: me ? me.display_name : "",
      status: "published",
      owner: true,
      favorited: false,
    },
    true
  );
}

async function boot() {
  // Show the gate immediately, before the counter request comes back.
  if (!token) showLanding();
  await refreshCounter();
  if (!token) return;
  const res = await api("GET", "/api/auth/me");
  if (!res.ok) {
    if (!res.loggedOut) showLanding(errorText(res.data));
    return;
  }
  me = res.data;
  await enterApp();
}

$("counterBtn").addEventListener("click", bumpCounter);
$("landingCounter").addEventListener("click", bumpCounter);
$("logo").addEventListener("click", function () { if (token) go("home"); });
$("nBrowse").addEventListener("click", function () { go("home"); });
$("nMine").addEventListener("click", function () { go("mine"); });
$("nNew").addEventListener("click", function () { openForm(null); });
$("mMine").addEventListener("click", function () { $("menu").classList.remove("open"); go("mine"); });
$("mDrafts").addEventListener("click", function () { $("menu").classList.remove("open"); go("drafts"); });
$("mFavs").addEventListener("click", function () { $("menu").classList.remove("open"); go("favs"); });
$("mLogout").addEventListener("click", async function () {
  $("menu").classList.remove("open");
  await api("POST", "/api/auth/logout");
  clearSession();
  showLanding();
});
$("userBtn").addEventListener("click", function (event) {
  event.stopPropagation();
  $("menu").classList.toggle("open");
});
document.addEventListener("click", function () { $("menu").classList.remove("open"); });

$("searchForm").addEventListener("submit", function (event) {
  event.preventDefault();
  if (view !== "home") view = "home";
  loadCrafts();
});
$("q").addEventListener("input", function () {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(function () {
    if (view === "home") loadCrafts();
  }, 250);
});

$("chips").addEventListener("click", function (event) {
  const button = event.target.closest("[data-chip]");
  if (!button) return;
  const name = button.getAttribute("data-chip");
  chip = name === chip && name !== "All" ? "All" : name;
  renderChips();
  loadCrafts();
});

function openCard(card) {
  const id = Number(card.getAttribute("data-id"));
  const craft = crafts.find(function (item) { return item.id === id; });
  if (craft && craft.status === "draft") openForm(craft);
  else openDetail(id);
}

$("grid").addEventListener("click", function (event) {
  const fav = event.target.closest("[data-fav]");
  if (fav) {
    toggleFav(Number(fav.getAttribute("data-fav")));
    return;
  }
  const card = event.target.closest(".card");
  if (card) openCard(card);
});
$("grid").addEventListener("keydown", function (event) {
  if (event.key !== "Enter" && event.key !== " ") return;
  const card = event.target.closest(".card");
  if (!card || event.target.closest("[data-fav]")) return;
  event.preventDefault();
  openCard(card);
});

document.addEventListener("error", function (event) {
  if (event.target && event.target.tagName === "IMG") event.target.classList.add("bad");
}, true);

$("catSel").addEventListener("click", function (event) {
  const button = event.target.closest("[data-cat]");
  if (!button) return;
  const name = button.getAttribute("data-cat");
  selectedCategory = selectedCategory === name ? "" : name;
  renderSelectors();
  $("fCat").classList.remove("err");
});
$("tagSel").addEventListener("click", function (event) {
  const button = event.target.closest("[data-tag]");
  if (!button) return;
  const name = button.getAttribute("data-tag");
  const index = selectedTags.indexOf(name);
  if (index >= 0) selectedTags.splice(index, 1);
  else selectedTags.push(name);
  renderSelectors();
  $("fTags").classList.remove("err");
});

$("fMap").addEventListener("click", function () {
  if (!$("iLoc").value.trim()) $("iLoc").value = "Toros, Mersin";
  if (!$("iLat").value.trim()) $("iLat").value = "36.8";
  if (!$("iLng").value.trim()) $("iLng").value = "34.0";
  placePin(true);
  $("fLoc").classList.remove("err");
});
$("iLoc").addEventListener("input", function () {
  placePin(!!$("iLoc").value.trim());
  $("fLoc").classList.remove("err");
});

$("saveDraft").addEventListener("click", function () { save("draft"); });
$("publishBtn").addEventListener("click", function () { save("published"); });
$("previewBtn").addEventListener("click", preview);

$("loginForm").addEventListener("submit", async function (event) {
  event.preventDefault();
  const res = await api("POST", "/api/auth/login", {
    email: $("loginEmail").value.trim(),
    password: $("loginPassword").value,
  });
  if (!res.ok) {
    showLanding(errorText(res.data));
    return;
  }
  saveSession(res.data);
  await enterApp();
  toast("Welcome back!");
});

$("registerForm").addEventListener("submit", async function (event) {
  event.preventDefault();
  const res = await api("POST", "/api/auth/register", {
    email: $("regEmail").value.trim(),
    password: $("regPassword").value,
    display_name: $("regName").value.trim(),
  });
  if (!res.ok) {
    showLanding(errorText(res.data));
    return;
  }
  saveSession(res.data);
  await enterApp();
  toast("Account created. Email verification is skipped in this prototype.");
});

$("showRegister").addEventListener("click", function () {
  const registering = $("registerForm").classList.contains("hide");
  setAuthMode(registering);
});

$("ovDet").addEventListener("click", function (event) {
  if (event.target === $("ovDet")) closeOv("ovDet");
});
$("ovRep").addEventListener("click", function (event) {
  if (event.target === $("ovRep")) closeOv("ovRep");
});
$("closeRep").addEventListener("click", function () { closeOv("ovRep"); });
$("cancelRep").addEventListener("click", function () { closeOv("ovRep"); });
$("submitRep").addEventListener("click", submitReport);

document.addEventListener("keydown", function (event) {
  if (event.key === "Escape") {
    closeOv("ovDet");
    closeOv("ovRep");
    $("menu").classList.remove("open");
  }
});

boot();
