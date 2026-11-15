/* Qayta Mini App: shell, theme, tab router, language switcher and hash routing.
   Plain browser script (no build step). Loaded after i18n.js and BEFORE map.js, prices.js, me.js.

   MODULE CONTRACT (for map.js, prices.js, me.js)
   ----------------------------------------------
   1. Each tab file registers itself on the global registry created here:
          window.QayTabs = window.QayTabs || {};
          QayTabs.map = { render: function (container, params) { ... }, destroy: function () { ... } };
      Tab names: "map", "prices", "me" and "report". The "report" screen is NOT a bottom-nav tab; it is
      opened by the hash #report (from the bot's /report keyboard button) and is registered by me.js
      as QayTabs.report (task 15.2), so index.html needs no extra script tag.
      "scan" is rendered by app.js itself.
   2. render(container, params)
        - container: an empty <section> element owned by the router. Fill it using textContent or the
          QayApp.el() helper; never put untrusted data into innerHTML.
        - params: plain object of string values parsed from the hash query, e.g. {material: "PET_1"}
          for #map?material=PET_1, {items: "3", reports: "1", rank: "7"} for #me?..., {type: "price"}
          for #report?type=price. Always an object, possibly empty. Values are untrusted strings.
        - It may be async (return a Promise); errors are caught and shown as a generic message.
   3. destroy() is optional. It is called before the tab is left or re-rendered (e.g. map.js removes its
      Leaflet map there).
   4. The router re-renders the active tab after a language change, so render() must read texts via t()
      each time it runs. Tab files are loaded after app.js, so routing starts on DOMContentLoaded.
   5. Helpers exposed on window.QayApp: parseHash, navigate(tab, params), rerender(), el(tag, attrs, kids),
      telegram() (the Telegram.WebApp object or null).
*/
"use strict";

var KNOWN_TABS = ["scan", "map", "prices", "me", "report"];
var NAV_TABS = ["scan", "map", "prices", "me"];
var DEFAULT_TAB = "scan";

/* Pure: "#map?material=PET_1" -> {tab: "map", params: {material: "PET_1"}}.
   Unknown or empty tab falls back to "scan". Telegram launch parameters (tgWebApp*) are ignored. */
function parseHash(hash) {
  var raw = String(hash === undefined || hash === null ? "" : hash);
  if (raw.charAt(0) === "#") raw = raw.slice(1);
  var qIndex = raw.indexOf("?");
  var name = qIndex >= 0 ? raw.slice(0, qIndex) : raw;
  var query = qIndex >= 0 ? raw.slice(qIndex + 1) : "";
  if (KNOWN_TABS.indexOf(name.toLowerCase()) >= 0) {
    name = name.toLowerCase();
  } else {
    // "#tgWebAppData=..." and other non-route hashes: use the default tab, keep only real params
    if (name.indexOf("=") >= 0 && !query) query = name;
    name = DEFAULT_TAB;
  }
  var params = {};
  var search = new URLSearchParams(query);
  search.forEach(function (value, key) {
    if (key.indexOf("tgWebApp") === 0) return;
    if (key === "__proto__" || key === "constructor" || key === "prototype") return;
    params[key] = value;
  });
  return { tab: name, params: params };
}

/* ---------- DOM helpers (safe: text only via textContent) ---------- */

function el(tag, attrs, kids) {
  var node = document.createElement(tag);
  if (attrs) {
    Object.keys(attrs).forEach(function (key) {
      var value = attrs[key];
      if (value === null || value === undefined || value === false) return;
      if (key === "text") node.textContent = String(value);
      else if (key === "class") node.className = String(value);
      else node.setAttribute(key, String(value));
    });
  }
  (kids || []).forEach(function (kid) {
    if (kid === null || kid === undefined) return;
    node.appendChild(typeof kid === "string" ? document.createTextNode(kid) : kid);
  });
  return node;
}

function telegram() {
  return typeof window !== "undefined" && window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
}

/* ---------- Telegram init and theme ---------- */

var THEME_MAP = {
  bg_color: "--color-bg",
  text_color: "--color-text",
  hint_color: "--color-muted",
  link_color: "--color-link",
  button_color: "--color-button",
  button_text_color: "--color-button-text",
  secondary_bg_color: "--color-surface"
};

function applyTheme() {
  var tg = telegram();
  if (!tg || !tg.themeParams) return;
  var style = document.documentElement.style;
  Object.keys(THEME_MAP).forEach(function (param) {
    var value = tg.themeParams[param];
    if (typeof value === "string" && /^#[0-9a-fA-F]{3,8}$/.test(value)) {
      style.setProperty(THEME_MAP[param], value);
    }
  });
}

function initTelegram() {
  var tg = telegram();
  if (!tg) return;
  try { tg.ready(); } catch (e) { /* ignore */ }
  try { tg.expand(); } catch (e) { /* ignore */ }
  applyTheme();
  try { if (tg.onEvent) tg.onEvent("themeChanged", applyTheme); } catch (e) { /* ignore */ }
}

/* ---------- Router ---------- */

var QayTabs = typeof window !== "undefined" ? (window.QayTabs = window.QayTabs || {}) : {};
var current = { tab: null, params: {}, view: null };

function destroyCurrent() {
  var tab = current.tab;
  if (tab && QayTabs[tab] && typeof QayTabs[tab].destroy === "function") {
    try { QayTabs[tab].destroy(); } catch (e) { /* ignore */ }
  }
}

function updateNav(tab) {
  document.querySelectorAll("#bottom-bar button[data-tab]").forEach(function (btn) {
    var active = btn.getAttribute("data-tab") === tab;
    btn.classList.toggle("active", active);
    if (active) btn.setAttribute("aria-current", "page");
    else btn.removeAttribute("aria-current");
  });
}

function renderLangSwitcher() {
  var active = getLang();
  var row = el("div", { class: "chip-row", role: "group", "aria-label": t("lang.title") });
  ["uz", "ru", "en"].forEach(function (lang) {
    var chip = el("button", {
      type: "button",
      class: "chip" + (lang === active ? " active" : ""),
      "data-lang": lang,
      "aria-pressed": lang === active ? "true" : "false",
      text: t("lang.name." + lang)
    });
    row.appendChild(chip);
  });
  return row;
}

function renderScan(container) {
  var steps = el("ol", null, ["scan.step1", "scan.step2", "scan.step3"].map(function (key) {
    return el("li", { text: t(key) });
  }));
  var button = el("button", { type: "button", class: "btn-block", id: "scan-close", text: t("scan.button") });
  container.appendChild(el("h1", { text: t("scan.title") }));
  container.appendChild(el("div", { class: "card" }, [el("p", { text: t("scan.text") }), steps]));
  container.appendChild(button);
}

function renderPlaceholder(container, key) {
  container.appendChild(el("div", { class: "loading", text: t(key) }));
}

function renderTabInto(view, tab, params) {
  if (tab === "scan") {
    renderScan(view);
    return;
  }
  var mod = QayTabs[tab];
  if (!mod || typeof mod.render !== "function") {
    renderPlaceholder(view, "common.loading");
    return;
  }
  try {
    var result = mod.render(view, params);
    if (result && typeof result.catch === "function") {
      result.catch(function () {
        view.textContent = "";
        view.appendChild(el("div", { class: "empty-state", text: t("common.error") }));
      });
    }
  } catch (e) {
    view.textContent = "";
    view.appendChild(el("div", { class: "empty-state", text: t("common.error") }));
  }
}

function route() {
  var parsed = parseHash(window.location.hash);
  destroyCurrent();
  var content = document.getElementById("tab-content");
  if (!content) return;
  content.textContent = "";
  content.appendChild(renderLangSwitcher());
  var view = el("section", { id: "tab-view", "data-tab-view": parsed.tab });
  content.appendChild(view);
  current = { tab: parsed.tab, params: parsed.params, view: view };
  updateNav(parsed.tab);
  document.documentElement.lang = getLang();
  renderTabInto(view, parsed.tab, parsed.params);
  applyI18n(document);
}

function navigate(tab, params) {
  var name = KNOWN_TABS.indexOf(tab) >= 0 ? tab : DEFAULT_TAB;
  var query = params ? new URLSearchParams(params).toString() : "";
  var hash = "#" + name + (query ? "?" + query : "");
  if (window.location.hash === hash) route();
  else window.location.hash = hash;
}

function onNavClick(event) {
  var btn = event.target.closest ? event.target.closest("button[data-tab]") : null;
  if (!btn) return;
  var tab = btn.getAttribute("data-tab");
  if (NAV_TABS.indexOf(tab) < 0) return;
  navigate(tab);
}

function onContentClick(event) {
  var target = event.target;
  var chip = target.closest ? target.closest("button[data-lang]") : null;
  if (chip) {
    setLang(chip.getAttribute("data-lang"));
    route();
    return;
  }
  if (target.closest && target.closest("#scan-close")) {
    var tg = telegram();
    if (tg && typeof tg.close === "function") tg.close();
    else window.close();
  }
}

function init() {
  initTelegram();
  var nav = document.getElementById("bottom-bar");
  var content = document.getElementById("tab-content");
  if (nav) nav.addEventListener("click", onNavClick);
  if (content) content.addEventListener("click", onContentClick);
  window.addEventListener("hashchange", route);
  route();
}

if (typeof window !== "undefined" && typeof document !== "undefined") {
  window.parseHash = parseHash;
  window.QayApp = {
    parseHash: parseHash,
    navigate: navigate,
    rerender: route,
    el: el,
    telegram: telegram
  };
  // Tab scripts load after this file, so wait until the whole document has been parsed.
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else setTimeout(init, 0);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { parseHash: parseHash };
}
