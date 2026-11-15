/* Qayta Mini App: Prices tab. Registers QayTabs.prices (see the module contract at the top of app.js).
   Shows only verified records from data/prices.json. Prices are never invented or estimated. */
"use strict";

// Same order as CATALOGUE in src/qayta/materials.py
var PRICE_MATERIALS = [
  "PET_1", "HDPE_2", "PP_5", "GLASS", "PAPER", "CARDBOARD", "ALUMINIUM",
  "STEEL", "BATTERIES", "EWASTE", "TEXTILES", "ORGANIC", "MIXED"
];
var OUTDATED_DAYS = 60;
var DAY_MS = 24 * 60 * 60 * 1000;

function parseIsoDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}/.test(value.trim())) return null;
  var ms = Date.parse(value.trim());
  return isNaN(ms) ? null : ms;
}

/* Pure: a record is usable only with a known material, a positive finite price, and a non-empty source and date. */
function isValidRecord(rec) {
  if (!rec || typeof rec !== "object") return false;
  if (PRICE_MATERIALS.indexOf(rec.material) < 0) return false;
  if (typeof rec.price_som_per_kg !== "number" || !isFinite(rec.price_som_per_kg) || rec.price_som_per_kg <= 0) return false;
  if (typeof rec.source !== "string" || !rec.source.trim()) return false;
  if (typeof rec.point_id !== "string" || !rec.point_id.trim()) return false;
  return parseIsoDate(rec.date) !== null;
}

/* Pure: true when the date is more than 60 days before `now` (Date or ms; default: current time). */
function isOutdated(dateStr, now) {
  var ms = parseIsoDate(dateStr);
  if (ms === null) return false;
  var nowMs = now instanceof Date ? now.getTime() : typeof now === "number" ? now : Date.now();
  return nowMs - ms > OUTDATED_DAYS * DAY_MS;
}

/* Pure: returns [{material, rows}] for every catalogue material, in catalogue order.
   Malformed records are dropped; rows are sorted by price, highest first. */
function groupByMaterial(records) {
  var list = Array.isArray(records) ? records : [];
  return PRICE_MATERIALS.map(function (material) {
    var rows = list.filter(function (rec) {
      return isValidRecord(rec) && rec.material === material;
    });
    rows.sort(function (a, b) { return b.price_som_per_kg - a.price_som_per_kg; });
    return { material: material, rows: rows };
  });
}

/* ---------- Rendering (browser only) ---------- */

function loadJson(url) {
  return fetch(url, { cache: "no-cache" }).then(function (res) {
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  });
}

function pointNameMap(points) {
  var map = {};
  (Array.isArray(points) ? points : []).forEach(function (p) {
    if (p && typeof p.id === "string" && typeof p.name === "string") map[p.id] = p.name;
  });
  return map;
}

function formatPrice(value) {
  return Math.round(value).toString().replace(/\B(?=(\d{3})+(?!\d))/g, " ");
}

function buildPriceRow(el, group, rec, names, first) {
  var dateCell = el("td", null, [rec.date.trim()]);
  if (isOutdated(rec.date)) {
    dateCell.appendChild(el("span", { class: "badge badge-warn", text: t("price.outdated") }));
  }
  return el("tr", null, [
    el("td", { text: first ? t("mat." + group.material) : "" }),
    el("td", { text: names[rec.point_id] || rec.point_id }),
    el("td", { text: formatPrice(rec.price_som_per_kg) }),
    el("td", { text: rec.source }),
    dateCell
  ]);
}

function buildEmptyRow(el, material) {
  return el("tr", null, [
    el("td", { text: t("mat." + material) }),
    el("td", { text: "—" }),
    el("td", { text: "—" }),
    el("td", { text: "—" }),
    el("td", { text: "—" })
  ]);
}

function buildTable(el, groups, names) {
  var head = el("tr", null, ["material", "point", "price", "source", "date"].map(function (col) {
    return el("th", { scope: "col", text: t("prices.col." + col) });
  }));
  var body = el("tbody");
  groups.forEach(function (group) {
    if (!group.rows.length) {
      body.appendChild(buildEmptyRow(el, group.material));
      return;
    }
    group.rows.forEach(function (rec, i) {
      body.appendChild(buildPriceRow(el, group, rec, names, i === 0));
    });
  });
  var table = el("table", { class: "price-table" }, [el("thead", null, [head]), body]);
  return el("div", { class: "table-wrap", style: "overflow-x:auto" }, [table]);
}

function renderPrices(container) {
  var el = window.QayApp.el;
  container.textContent = "";
  container.appendChild(el("h1", { text: t("prices.title") }));
  var holder = el("div", { class: "loading", text: t("common.loading") });
  container.appendChild(holder);

  var pricesReq = loadJson("data/prices.json");
  var pointsReq = loadJson("data/points.json").catch(function () { return []; });
  return Promise.all([pricesReq, pointsReq]).then(function (results) {
    var groups = groupByMaterial(results[0]);
    var names = pointNameMap(results[1]);
    var missing = groups.some(function (g) { return !g.rows.length; });
    holder.textContent = "";
    holder.className = "";
    holder.appendChild(buildTable(el, groups, names));
    if (missing) {
      holder.appendChild(el("p", { class: "hint", text: t("prices.empty") }));
    }
    holder.appendChild(el("p", { class: "hint", text: t("prices.note") }));
    var link = el("button", { type: "button", class: "btn-block", id: "prices-report", text: t("prices.report_link") });
    link.addEventListener("click", function () {
      window.QayApp.navigate("report", { type: "price" });
    });
    holder.appendChild(link);
  }).catch(function () {
    holder.textContent = "";
    holder.className = "empty-state";
    holder.appendChild(el("p", { text: t("common.error") }));
    holder.appendChild(el("p", { class: "hint", text: t("prices.empty") }));
  });
}

if (typeof window !== "undefined" && typeof document !== "undefined") {
  window.QayTabs = window.QayTabs || {};
  window.QayTabs.prices = { render: renderPrices };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    groupByMaterial: groupByMaterial,
    isOutdated: isOutdated,
    isValidRecord: isValidRecord,
    PRICE_MATERIALS: PRICE_MATERIALS
  };
}
