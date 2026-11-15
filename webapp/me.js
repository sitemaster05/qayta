/* Qayta Mini App: Me tab. Registers QayTabs.me (see the module contract at the top of app.js).
   Numbers come from the bot's /stats button as #me?items=..&reports=..&rank=.. and are untrusted:
   each is accepted only as a plain non-negative integer up to MAX_VALUE, otherwise ignored.

   Points mirror src/qayta/impact.py: points = counted_items + 5 * approved_reports.
   The hash carries only the raw "items sorted" counter, so the Mini App uses items as counted_items.
   The bot counts at most 20 items per day towards points, so /stats may show fewer points than this
   screen. The value here is an approximation of total_points. Points have no cash value. */
(function () {
  "use strict";

  var REPORT_POINTS = 5;
  var MAX_VALUE = 1000000;

  // (threshold, locale key) ascending, same as LEVELS in impact.py
  var LEVELS = [
    [0, "level.beginner"],
    [10, "level.recycler"],
    [50, "level.champion"],
    [100, "level.legend"]
  ];

  /* Pure: counted items plus 5 per approved report. */
  function totalPoints(countedItems, approvedReports) {
    return countedItems + REPORT_POINTS * approvedReports;
  }

  /* Pure: locale key of the highest level whose threshold is <= points. */
  function getLevel(points) {
    for (var i = LEVELS.length - 1; i >= 0; i--) {
      if (points >= LEVELS[i][0]) return LEVELS[i][1];
    }
    return LEVELS[0][1];
  }

  /* Pure: the first level above points as [threshold, key], or null at the top level. */
  function nextLevel(points) {
    for (var i = 0; i < LEVELS.length; i++) {
      if (LEVELS[i][0] > points) return LEVELS[i];
    }
    return null;
  }

  /* Pure: untrusted string -> integer in [0, MAX_VALUE], or null when invalid. */
  function parseCount(value) {
    if (typeof value !== "string" || !/^\d{1,7}$/.test(value)) return null;
    var n = parseInt(value, 10);
    return n <= MAX_VALUE ? n : null;
  }

  /* Pure: rank must be a positive integer. */
  function parseRank(value) {
    var n = parseCount(value);
    return n !== null && n >= 1 ? n : null;
  }

  /* Pure: {items, reports, rank} with nulls for invalid values, or null when there is nothing to show. */
  function parseStats(params) {
    var p = params && typeof params === "object" ? params : {};
    var items = parseCount(p.items);
    var reports = parseCount(p.reports);
    if (items === null && reports === null) return null;
    return { items: items || 0, reports: reports || 0, rank: parseRank(p.rank) };
  }

  /* ---------- Report payloads (mirror parse_report in src/qayta/bot.py) ---------- */

  var MATERIAL_KEYS = ["PET_1", "HDPE_2", "PP_5", "GLASS", "PAPER", "CARDBOARD", "ALUMINIUM", "STEEL",
    "BATTERIES", "EWASTE", "TEXTILES", "ORGANIC", "MIXED"];
  var MAX_NAME = 100;
  var MAX_PHONE = 30;
  var MAX_HOURS = 100;
  var MAX_POINT_ID = 64;
  var MAX_PRICE = 10000000;
  var MAX_JSON = 4096;

  function fail() { return { ok: false, error: "report.required" }; }

  /* Pure: string/number -> finite number, or null (empty and non-numeric input are rejected). */
  function toNumber(value) {
    if (typeof value === "number") return isFinite(value) ? value : null;
    if (typeof value !== "string") return null;
    var s = value.trim().replace(",", ".");
    if (s === "") return null;
    var n = Number(s);
    return isFinite(n) ? n : null;
  }

  /* Pure: trimmed string within max length; "" allowed only when not required; null when invalid. */
  function cleanStr(value, max, required) {
    if (value === undefined || value === null) value = "";
    if (typeof value !== "string") return null;
    var s = value.trim();
    if (s.length > max || (required && s === "")) return null;
    return s;
  }

  function finish(payload) {
    var json = JSON.stringify(payload);
    if (json.length > MAX_JSON) return fail();
    return { ok: true, payload: payload, json: json };
  }

  /* Pure: fields {name, lat, lon, materials[], phone, hours} -> {ok, payload, json} | {ok:false, error}. */
  function buildPointPayload(fields) {
    var f = fields && typeof fields === "object" ? fields : {};
    var name = cleanStr(f.name, MAX_NAME, true);
    var phone = cleanStr(f.phone, MAX_PHONE, false);
    var hours = cleanStr(f.hours, MAX_HOURS, false);
    var lat = toNumber(f.lat);
    var lon = toNumber(f.lon);
    if (name === null || phone === null || hours === null) return fail();
    if (lat === null || lon === null || lat < -90 || lat > 90 || lon < -180 || lon > 180) return fail();
    var list = Array.isArray(f.materials) ? f.materials : [];
    var materials = [];
    for (var i = 0; i < list.length; i++) {
      if (MATERIAL_KEYS.indexOf(list[i]) < 0) return fail();
      if (materials.indexOf(list[i]) < 0) materials.push(list[i]);
    }
    if (materials.length < 1 || materials.length > MATERIAL_KEYS.length) return fail();
    var payload = { type: "point", name: name, lat: lat, lon: lon, materials: materials };
    if (phone) payload.phone = phone;
    if (hours) payload.hours = hours;
    return finish(payload);
  }

  /* Pure: fields {point_id, material, price} -> {ok, payload, json} | {ok:false, error}. */
  function buildPricePayload(fields) {
    var f = fields && typeof fields === "object" ? fields : {};
    var pointId = cleanStr(f.point_id, MAX_POINT_ID, true);
    var price = toNumber(f.price);
    if (pointId === null || MATERIAL_KEYS.indexOf(f.material) < 0) return fail();
    if (price === null || !(price > 0) || price > MAX_PRICE) return fail();
    return finish({ type: "price", point_id: pointId, material: f.material, price_som_per_kg: price });
  }

  /* sendData works only for pages opened from a reply-keyboard button (non-empty initData). */
  function canSendData() {
    var tg = window.QayApp.telegram();
    return !!(tg && tg.initData && typeof tg.sendData === "function");
  }

  /* ---------- Report screen (browser only) ---------- */

  function field(el, id, labelKey, attrs) {
    var input = el("input", Object.assign({ id: id, type: "text" }, attrs || {}));
    return { input: input, row: el("label", { class: "field", for: id }, [el("span", { text: t(labelKey) }), input]) };
  }

  function switcher(el, type) {
    var kids = [["point", "report.point_form"], ["price", "report.price_form"]].map(function (item) {
      var btn = el("button", { type: "button", class: "chip" + (item[0] === type ? " active" : ""), text: t(item[1]) });
      btn.addEventListener("click", function () { window.QayApp.navigate("report", { type: item[0] }); });
      return btn;
    });
    return el("div", { class: "chips" }, kids);
  }

  function showError(el, container) {
    var old = container.querySelector(".report-error");
    if (old) old.remove();
    container.appendChild(el("p", { class: "muted report-error", role: "alert", text: t("report.required") }));
  }

  function submitButton(el, container, build) {
    var btn = el("button", { type: "button", class: "btn", text: t("report.submit") });
    btn.addEventListener("click", function () {
      var result = build();
      if (!result.ok) { showError(el, container); return; }
      try { window.QayApp.telegram().sendData(result.json); } catch (e) { showError(el, container); }
    });
    return btn;
  }

  function pointForm(el, container) {
    var name = field(el, "rp-name", "report.name", { maxlength: MAX_NAME });
    var lat = field(el, "rp-lat", "report.lat", { inputmode: "decimal" });
    var lon = field(el, "rp-lon", "report.lon", { inputmode: "decimal" });
    var phone = field(el, "rp-phone", "report.phone", { maxlength: MAX_PHONE, type: "tel" });
    var hours = field(el, "rp-hours", "report.hours", { maxlength: MAX_HOURS });
    var boxes = MATERIAL_KEYS.map(function (key) {
      var cb = el("input", { type: "checkbox", value: key });
      return { key: key, cb: cb, row: el("label", { class: "check" }, [cb, el("span", { text: t("mat." + key) })]) };
    });
    var kids = [name.row, lat.row, lon.row];
    if (typeof navigator !== "undefined" && navigator.geolocation) {
      var geo = el("button", { type: "button", class: "chip", text: "📍" });
      geo.addEventListener("click", function () {
        navigator.geolocation.getCurrentPosition(function (pos) {
          lat.input.value = pos.coords.latitude.toFixed(5);
          lon.input.value = pos.coords.longitude.toFixed(5);
        }, function () { /* ignore: user can type coordinates */ });
      });
      kids.push(geo);
    }
    kids.push(el("p", { text: t("report.materials") }));
    boxes.forEach(function (b) { kids.push(b.row); });
    kids.push(phone.row, hours.row);
    var form = el("div", { class: "card" }, kids);
    form.appendChild(submitButton(el, form, function () {
      return buildPointPayload({
        name: name.input.value, lat: lat.input.value, lon: lon.input.value,
        materials: boxes.filter(function (b) { return b.cb.checked; }).map(function (b) { return b.key; }),
        phone: phone.input.value, hours: hours.input.value
      });
    }));
    container.appendChild(form);
  }

  function priceForm(el, container, points) {
    var pointRow;
    var getPoint;
    if (points.length) {
      var select = el("select", { id: "rr-point" }, points.map(function (p) {
        return el("option", { value: p.id, text: p.name });
      }));
      pointRow = el("label", { class: "field", for: "rr-point" }, [el("span", { text: t("report.point") }), select]);
      getPoint = function () { return select.value; };
    } else {
      var free = field(el, "rr-point", "report.point", { maxlength: MAX_POINT_ID });
      pointRow = free.row;
      getPoint = function () { return free.input.value; };
    }
    var material = el("select", { id: "rr-material" }, MATERIAL_KEYS.map(function (key) {
      return el("option", { value: key, text: t("mat." + key) });
    }));
    var price = field(el, "rr-price", "report.price", { inputmode: "decimal" });
    var form = el("div", { class: "card" }, [
      pointRow,
      el("label", { class: "field", for: "rr-material" }, [el("span", { text: t("report.material") }), material]),
      price.row
    ]);
    form.appendChild(submitButton(el, form, function () {
      return buildPricePayload({ point_id: getPoint(), material: material.value, price: price.input.value });
    }));
    container.appendChild(form);
  }

  /* Pure: points.json records -> [{id, name}] with usable string ids only. */
  function pointOptions(data) {
    if (!Array.isArray(data)) return [];
    return data.filter(function (p) {
      return p && typeof p.id === "string" && p.id && p.id.length <= MAX_POINT_ID;
    }).map(function (p) { return { id: p.id, name: typeof p.name === "string" && p.name ? p.name : p.id }; });
  }

  function loadPoints() {
    return fetch("data/points.json", { cache: "no-cache" })
      .then(function (res) { if (!res.ok) throw new Error("HTTP " + res.status); return res.json(); })
      .then(pointOptions)
      .catch(function () { return []; });
  }

  function renderReport(container, params) {
    var el = window.QayApp.el;
    var type = params && params.type === "price" ? "price" : "point";
    container.textContent = "";
    if (!canSendData()) {
      container.appendChild(el("div", { class: "card" }, [el("p", { text: t("report.use_command") })]));
      return;
    }
    container.appendChild(switcher(el, type));
    if (type === "point") { pointForm(el, container); return; }
    return loadPoints().then(function (points) { priceForm(el, container, points); });
  }

  /* ---------- Rendering (browser only) ---------- */

  function statBox(el, value, labelKey) {
    return el("div", { class: "stat" }, [
      el("span", { class: "value", text: String(value) }),
      el("span", { class: "label", text: t(labelKey) })
    ]);
  }

  function thresholdRows(el, points) {
    var current = getLevel(points);
    return LEVELS.map(function (level) {
      var kids = [
        el("div", { class: "grow" }, [el("div", { class: "title", text: t(level[1]) })]),
        el("div", { class: "end", text: t("me.points_short", { n: level[0] }) })
      ];
      if (level[1] === current) kids.splice(1, 0, el("span", { class: "badge", text: "✓" }));
      return el("div", { class: "list-row" }, kids);
    });
  }

  function renderNoData(el, container) {
    container.appendChild(el("div", { class: "card" }, [
      el("p", { text: t("me.no_data") }),
      el("p", { class: "muted", text: t("me.leaderboard_hint") })
    ]));
  }

  function renderStats(el, container, stats) {
    var points = totalPoints(stats.items, stats.reports);
    var next = nextLevel(points);

    container.appendChild(el("div", { class: "card" }, [
      el("span", { class: "badge", text: t(getLevel(points)) }),
      stats.rank !== null ? el("p", { text: t("me.rank", { rank: stats.rank }) }) : null,
      el("p", {
        class: "muted",
        text: next ? t("me.next_level", { n: next[0] - points }) : t("me.max_level")
      })
    ]));

    container.appendChild(el("div", { class: "stat-grid" }, [
      statBox(el, stats.items, "stats.items"),
      statBox(el, stats.reports, "stats.reports"),
      statBox(el, points, "stats.points")
    ]));

    container.appendChild(el("div", { class: "card" }, [
      el("h2", { text: t("me.thresholds") }),
      el("div", { class: "list" }, thresholdRows(el, points))
    ]));

    container.appendChild(el("p", { class: "muted", text: t("me.points_note") }));
    container.appendChild(el("p", { class: "muted", text: t("me.leaderboard_hint") }));
  }

  function renderMe(container, params) {
    var el = window.QayApp.el;
    container.textContent = "";
    container.appendChild(el("h1", { text: t("me.title") }));
    var stats = parseStats(params);
    if (stats) renderStats(el, container, stats);
    else renderNoData(el, container);
  }

  if (typeof window !== "undefined" && typeof document !== "undefined") {
    window.QayTabs = window.QayTabs || {};
    window.QayTabs.me = { render: renderMe };

    window.QayTabs.report = { render: renderReport };
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = {
      getLevel: getLevel,
      totalPoints: totalPoints,
      nextLevel: nextLevel,
      parseCount: parseCount,
      parseStats: parseStats,
      buildPointPayload: buildPointPayload,
      buildPricePayload: buildPricePayload,
      pointOptions: pointOptions,
      LEVELS: LEVELS
    };
  }
})();
