/* Qayta Mini App: Map tab (Leaflet + OpenStreetMap + curated points + live Overpass).
   Registers window.QayTabs.map = { render(container, params), destroy() } (see the contract in app.js).
   Pure helpers (haversine, mergePoints, sortPoints, buildOverpassQuery, bestPrice, ...) are exported
   through a guarded module.exports so they can be tested with node. */
(function (root) {
  "use strict";

  var OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
  ];
  var OVERPASS_TIMEOUT_S = 25;
  var RADIUS_M = 5000;
  var DEDUPE_M = 30;
  var STALE_DAYS = 60;
  var DAY_MS = 86400000;

  /* Same mapping as src/qayta/materials.py (osm_tag per catalogue key). */
  var MATERIAL_OSM_TAGS = {
    PET_1: "recycling:plastic_bottles",
    HDPE_2: "recycling:plastic",
    PP_5: "recycling:plastic",
    GLASS: "recycling:glass",
    PAPER: "recycling:paper",
    CARDBOARD: "recycling:cardboard",
    ALUMINIUM: "recycling:aluminium",
    STEEL: "recycling:scrap_metal",
    BATTERIES: "recycling:batteries",
    EWASTE: "recycling:electrical_appliances",
    TEXTILES: "recycling:clothes",
    ORGANIC: "recycling:organic",
    MIXED: "recycling:waste"
  };
  var MATERIAL_KEYS = Object.keys(MATERIAL_OSM_TAGS);

  var CITIES = {
    tashkent: { lat: 41.2995, lon: 69.2401 },
    ohangaron: { lat: 40.9064, lon: 69.6378 },
    samarkand: { lat: 39.6542, lon: 66.9597 }
  };

  /* ---------------- pure helpers ---------------- */

  function isNum(value) {
    return typeof value === "number" && isFinite(value);
  }

  function haversine(lat1, lon1, lat2, lon2) {
    var R = 6371000;
    var rad = Math.PI / 180;
    var dLat = (lat2 - lat1) * rad;
    var dLon = (lon2 - lon1) * rad;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(a)));
  }

  function buildOverpassQuery(lat, lon, radiusM) {
    var around = "(around:" + Math.round(radiusM) + "," + Number(lat).toFixed(5) + "," + Number(lon).toFixed(5) + ")";
    return "[out:json][timeout:" + OVERPASS_TIMEOUT_S + "];(" +
      'nwr["amenity"="recycling"]' + around + ";" +
      'nwr["shop"="scrap"]' + around + ";" +
      ");out center tags;";
  }

  /* Overpass element -> point, or null when it has no usable coordinates. */
  function normalizeOverpass(element) {
    if (!element || typeof element !== "object") return null;
    var lat = isNum(element.lat) ? element.lat : (element.center ? element.center.lat : undefined);
    var lon = isNum(element.lon) ? element.lon : (element.center ? element.center.lon : undefined);
    if (!isNum(lat) || !isNum(lon) || !element.type || element.id === undefined) return null;
    var tags = element.tags || {};
    var materials = [];
    MATERIAL_KEYS.forEach(function (key) {
      if (tags[MATERIAL_OSM_TAGS[key]] === "yes") materials.push(key);
    });
    return {
      id: element.type + "/" + element.id,
      osm_ref: element.type + "/" + element.id,
      name: tags.name || tags.operator || tags.brand || "",
      lat: lat,
      lon: lon,
      materials: materials,
      phone: tags.phone || tags["contact:phone"] || "",
      hours: tags.opening_hours || "",
      curated: false
    };
  }

  function normalizeCurated(record) {
    if (!record || typeof record !== "object" || typeof record.id !== "string") return null;
    if (!isNum(record.lat) || !isNum(record.lon)) return null;
    return {
      id: record.id,
      osm_ref: typeof record.osm_id === "string" ? record.osm_id : "",
      name: typeof record.name === "string" ? record.name : "",
      lat: record.lat,
      lon: record.lon,
      materials: Array.isArray(record.materials) ? record.materials.filter(function (m) { return typeof m === "string"; }) : [],
      phone: typeof record.phone === "string" ? record.phone : "",
      hours: typeof record.hours === "string" ? record.hours : "",
      verified_date: typeof record.verified_date === "string" ? record.verified_date : "",
      source: typeof record.source === "string" ? record.source : "",
      curated: true
    };
  }

  /* Curated records win by id. A live point is dropped when it has the same id as a curated point,
     points to the same OSM element, or lies within DEDUPE_M metres of one. */
  function mergePoints(curated, live) {
    var result = (curated || []).slice();
    var ids = {};
    result.forEach(function (p) {
      ids[p.id] = true;
      if (p.osm_ref) ids[p.osm_ref] = true;
    });
    (live || []).forEach(function (p) {
      if (ids[p.id] || (p.osm_ref && ids[p.osm_ref])) return;
      for (var i = 0; i < curated.length; i++) {
        if (haversine(p.lat, p.lon, curated[i].lat, curated[i].lon) <= DEDUPE_M) return;
      }
      result.push(p);
    });
    return result;
  }

  /* Returns new objects with distance_m (when origin is known) and `known` (true when the point is known
     to accept the material, or when no material is selected). Points with known materials that exclude the
     selected one are removed; points with unknown materials stay, after the known ones. */
  function sortPoints(points, material, origin) {
    var out = [];
    (points || []).forEach(function (p) {
      var accepts = !material || p.materials.indexOf(material) >= 0;
      var unknown = p.materials.length === 0;
      if (material && !accepts && !unknown) return;
      var copy = {};
      Object.keys(p).forEach(function (k) { copy[k] = p[k]; });
      copy.known = !material || accepts;
      if (origin) copy.distance_m = haversine(origin.lat, origin.lon, p.lat, p.lon);
      out.push(copy);
    });
    out.forEach(function (p, i) { p._i = i; });
    out.sort(function (a, b) {
      if (a.known !== b.known) return a.known ? -1 : 1;
      if (origin && a.distance_m !== b.distance_m) return a.distance_m - b.distance_m;
      return a._i - b._i;
    });
    out.forEach(function (p) { delete p._i; });
    return out;
  }

  function parseDate(text) {
    if (typeof text !== "string" || !/^\d{4}-\d{2}-\d{2}/.test(text)) return null;
    var ms = Date.parse(text.slice(0, 10) + "T00:00:00Z");
    return isFinite(ms) ? ms : null;
  }

  /* Highest valid price for the material (optionally for one point). A record is valid when the price is a
     positive finite number and it has a source and a parseable date. Never estimates. */
  function bestPrice(prices, material, opts) {
    if (!material || !Array.isArray(prices)) return null;
    var pointId = opts && opts.pointId;
    var now = opts && isNum(opts.now) ? opts.now : Date.now();
    var best = null;
    prices.forEach(function (r) {
      if (!r || r.material !== material) return;
      if (pointId && r.point_id !== pointId) return;
      if (!isNum(r.price_som_per_kg) || r.price_som_per_kg <= 0) return;
      if (typeof r.source !== "string" || !r.source || parseDate(r.date) === null) return;
      if (!best || r.price_som_per_kg > best.price) {
        best = { price: r.price_som_per_kg, source: r.source, date: r.date, point_id: r.point_id };
      }
    });
    if (best) best.outdated = now - parseDate(best.date) > STALE_DAYS * DAY_MS;
    return best;
  }

  function formatDistance(m) {
    return m < 1000 ? Math.round(m) + " m" : (m / 1000).toFixed(1) + " km";
  }

  var helpers = {
    haversine: haversine,
    mergePoints: mergePoints,
    sortPoints: sortPoints,
    buildOverpassQuery: buildOverpassQuery,
    bestPrice: bestPrice,
    normalizeOverpass: normalizeOverpass,
    normalizeCurated: normalizeCurated,
    MATERIAL_OSM_TAGS: MATERIAL_OSM_TAGS
  };

  if (typeof module !== "undefined" && module.exports) module.exports = helpers;
  if (typeof window === "undefined" || typeof document === "undefined") return;

  /* ---------------- browser part ---------------- */

  var state = null; // per-render state; null when destroyed
  var overpassQueue = Promise.resolve(); // one Overpass request at a time

  function el(tag, attrs, kids) { return root.QayApp.el(tag, attrs, kids); }
  function tg() { return root.QayApp.telegram(); }
  function tr(key, params) { return root.t(key, params); }

  function fetchJson(url) {
    return fetch(url, { cache: "no-cache" }).then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    });
  }

  function loadJsonArray(url) {
    return fetchJson(url).then(function (data) { return Array.isArray(data) ? data : []; })
      .catch(function () { return []; });
  }

  function fetchOverpassOnce(endpoint, query) {
    var controller = typeof AbortController !== "undefined" ? new AbortController() : null;
    var timer = setTimeout(function () { if (controller) controller.abort(); }, OVERPASS_TIMEOUT_S * 1000);
    return fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: "data=" + encodeURIComponent(query),
      signal: controller ? controller.signal : undefined
    }).then(function (res) {
      if (!res.ok) throw new Error("HTTP " + res.status);
      return res.json();
    }).then(function (data) {
      clearTimeout(timer);
      return data;
    }, function (err) {
      clearTimeout(timer);
      throw err;
    });
  }

  function fetchOverpass(lat, lon) {
    var query = buildOverpassQuery(lat, lon, RADIUS_M);
    var job = overpassQueue.then(function () {
      var attempt = function (i) {
        if (i >= OVERPASS_ENDPOINTS.length) return Promise.reject(new Error("overpass"));
        return fetchOverpassOnce(OVERPASS_ENDPOINTS[i], query).catch(function () { return attempt(i + 1); });
      };
      return attempt(0);
    }).then(function (data) {
      var elements = data && Array.isArray(data.elements) ? data.elements : [];
      return elements.map(normalizeOverpass).filter(Boolean);
    });
    overpassQueue = job.catch(function () { /* keep the queue alive */ });
    return job;
  }

  function withTimeout(promise, ms) {
    return new Promise(function (resolve) {
      var done = false;
      var timer = setTimeout(function () { if (!done) { done = true; resolve(null); } }, ms);
      promise.then(function (v) { if (!done) { done = true; clearTimeout(timer); resolve(v); } },
        function () { if (!done) { done = true; clearTimeout(timer); resolve(null); } });
    });
  }

  function telegramLocation() {
    var app = tg();
    var lm = app && app.LocationManager;
    if (!lm || typeof lm.init !== "function" || typeof lm.getLocation !== "function") return Promise.resolve(null);
    return withTimeout(new Promise(function (resolve) {
      lm.init(function () {
        lm.getLocation(function (data) {
          resolve(data && isNum(data.latitude) && isNum(data.longitude)
            ? { lat: data.latitude, lon: data.longitude } : null);
        });
      });
    }), 10000);
  }

  function browserLocation() {
    if (!root.navigator || !root.navigator.geolocation) return Promise.resolve(null);
    return withTimeout(new Promise(function (resolve, reject) {
      root.navigator.geolocation.getCurrentPosition(function (pos) {
        resolve({ lat: pos.coords.latitude, lon: pos.coords.longitude });
      }, reject, { timeout: 10000, maximumAge: 60000 });
    }), 12000);
  }

  function locate() {
    return telegramLocation().then(function (pos) { return pos || browserLocation(); });
  }

  function openUrl(event, url) {
    var app = tg();
    if (app && typeof app.openLink === "function") {
      event.preventDefault();
      app.openLink(url);
    }
  }

  function link(url, text) {
    var a = el("a", { href: url, target: "_blank", rel: "noopener noreferrer", text: text });
    a.addEventListener("click", function (event) { openUrl(event, url); });
    return a;
  }

  function osmUrl(p) {
    if (p.osm_ref && /^(node|way|relation)\/\d+$/.test(p.osm_ref)) return "https://www.openstreetmap.org/" + p.osm_ref;
    return "https://www.openstreetmap.org/?mlat=" + p.lat + "&mlon=" + p.lon + "#map=18/" + p.lat + "/" + p.lon;
  }

  function routeUrl(p, origin) {
    var from = origin ? origin.lat.toFixed(5) + "," + origin.lon.toFixed(5) : "";
    return "https://www.openstreetmap.org/directions?engine=fossgis_osrm_foot&route=" +
      encodeURIComponent(from + ";" + p.lat + "," + p.lon);
  }

  function materialLabels(keys) {
    return keys.map(function (k) { return tr("mat." + k); }).join(", ");
  }

  function buildPopup(p, material, prices, origin) {
    var box = el("div", { class: "popup" });
    box.appendChild(el("strong", { text: p.name || "OpenStreetMap" }));
    if (p.distance_m !== undefined) {
      box.appendChild(el("div", { text: tr("map.distance") + ": " + formatDistance(p.distance_m) }));
    }
    if (p.materials.length) {
      box.appendChild(el("div", { text: tr("map.accepts") + ": " + materialLabels(p.materials) }));
    } else {
      box.appendChild(el("div", { class: "badge badge-warn", text: tr("map.materials_unknown") }));
    }
    if (p.phone) box.appendChild(el("div", { text: tr("map.phone") + ": " + p.phone }));
    if (p.hours) box.appendChild(el("div", { text: tr("map.hours") + ": " + p.hours }));
    if (p.curated && p.verified_date) {
      box.appendChild(el("div", { class: "badge", text: "✓ " + tr("map.verified_on", { date: p.verified_date }) }));
    }
    var price = p.curated ? bestPrice(prices, material, { pointId: p.id }) : null;
    if (price) {
      var line = tr("price.line", { price: price.price, source: price.source, date: price.date });
      if (price.outdated) line += " (" + tr("price.outdated") + ")";
      box.appendChild(el("div", { text: line }));
    }
    var links = el("div", null, [link(routeUrl(p, origin), tr("map.route")), " · ", link(osmUrl(p), tr("map.open_osm"))]);
    box.appendChild(links);
    return box;
  }

  function redraw() {
    var s = state;
    if (!s || !s.map) return;
    s.layer.clearLayers();
    var sorted = sortPoints(mergePoints(s.curated, s.live), s.material, s.origin);
    sorted.forEach(function (p) {
      var marker = root.L.marker([p.lat, p.lon], { opacity: p.known ? 1 : 0.6 });
      marker.bindPopup(buildPopup(p, s.material, s.prices, s.origin));
      marker.addTo(s.layer);
    });
    var notes = [];
    if (!s.origin) notes.push(tr("map.no_location"));
    if (s.overpassFailed) notes.push(tr("map.overpass_failed"));
    if (s.loading) notes.push(tr("map.loading_points"));
    else if (!sorted.length) notes.push(tr("map.no_points"));
    s.status.textContent = notes.join(" ");
  }

  function setOrigin(pos, fromUser) {
    var s = state;
    if (!s) return;
    s.origin = pos;
    s.live = [];
    s.overpassFailed = false;
    s.loading = true;
    if (s.userMarker) s.map.removeLayer(s.userMarker);
    s.userMarker = root.L.circleMarker([pos.lat, pos.lon], { radius: 8, color: "#4caf75", fillOpacity: 0.8 }).addTo(s.map);
    s.map.setView([pos.lat, pos.lon], fromUser === "city" ? 12 : 14);
    redraw();
    var mine = s;
    fetchOverpass(pos.lat, pos.lon).then(function (points) {
      if (state !== mine || mine.origin !== pos) return;
      mine.live = points;
    }, function () {
      if (state !== mine || mine.origin !== pos) return;
      mine.overpassFailed = true;
    }).then(function () {
      if (state !== mine || mine.origin !== pos) return;
      mine.loading = false;
      redraw();
    });
  }

  function buildControls(s, params) {
    var select = el("select", { id: "map-material", "aria-label": tr("map.choose_material") });
    select.appendChild(el("option", { value: "", text: tr("map.all_materials") }));
    MATERIAL_KEYS.forEach(function (key) {
      select.appendChild(el("option", { value: key, text: tr("mat." + key) }));
    });
    var initial = params && MATERIAL_OSM_TAGS[params.material] ? params.material : "";
    select.value = initial;
    s.material = initial;
    select.addEventListener("change", function () {
      s.material = select.value;
      redraw();
    });
    return select;
  }

  function buildCityPicker() {
    var row = el("div", { class: "chip-row" });
    row.appendChild(el("span", { class: "muted", text: tr("map.pick_city") }));
    Object.keys(CITIES).forEach(function (name) {
      var chip = el("button", { type: "button", class: "chip", text: tr("map.city." + name) });
      chip.addEventListener("click", function () { setOrigin({ lat: CITIES[name].lat, lon: CITIES[name].lon }, "city"); });
      row.appendChild(chip);
    });
    return row;
  }

  function render(container, params) {
    destroy();
    var s = { curated: [], live: [], prices: [], origin: null, material: "", loading: false, overpassFailed: false };
    state = s;
    var select = buildControls(s, params);
    s.status = el("p", { class: "muted", role: "status" });
    var mapDiv = el("div", { id: "map", class: "map-container" });
    container.appendChild(el("h1", { text: tr("map.title") }));
    container.appendChild(select);
    container.appendChild(s.status);
    container.appendChild(mapDiv);

    if (!root.L) {
      s.status.textContent = tr("common.error");
      return Promise.resolve();
    }
    var start = CITIES.tashkent;
    s.map = root.L.map(mapDiv).setView([start.lat, start.lon], 11);
    root.L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "© OpenStreetMap contributors"
    }).addTo(s.map);
    s.layer = root.L.layerGroup().addTo(s.map);
    s.map.on("click", function (event) { setOrigin({ lat: event.latlng.lat, lon: event.latlng.lng }, "tap"); });
    s.status.textContent = tr("map.loading_points");

    return Promise.all([loadJsonArray("data/points.json"), loadJsonArray("data/prices.json")]).then(function (res) {
      if (state !== s) return null;
      s.curated = res[0].map(normalizeCurated).filter(Boolean);
      s.prices = res[1];
      redraw();
      return locate();
    }).then(function (pos) {
      if (state !== s) return;
      if (pos) {
        setOrigin(pos, "gps");
      } else {
        container.insertBefore(buildCityPicker(), mapDiv);
        redraw();
      }
    });
  }

  function destroy() {
    var s = state;
    state = null;
    if (s && s.map) {
      try { s.map.remove(); } catch (e) { /* ignore */ }
      s.map = null;
    }
  }

  root.QayTabs = root.QayTabs || {};
  root.QayTabs.map = { render: render, destroy: destroy };
})(typeof window !== "undefined" ? window : globalThis);
