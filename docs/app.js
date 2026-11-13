/* Berlin Airbnb dashboard: vanilla JS + hand-built SVG charts (no external libraries). */
(function () {
  "use strict";
  var $ = function (s) { return document.querySelector(s); };
  var fmt = function (n) { return Number(n).toLocaleString("en-US"); };
  var euro = function (n) { return "€" + fmt(Math.round(n)); };
  var LIC_COLORS = { "Registration number": "#12a150", "Business / host disclosure": "#2f6fed", "Exempt": "#9b8afb", "Other": "#98a2b3", "Missing": "#ff5a5f" };
  var FEATURE_LABELS = { minimum_nights: "Minimum stay", accommodates: "Guests", room_type: "Room type", bedrooms: "Bedrooms", district: "District", review_score: "Review score", amenities_count: "Amenities", bathrooms: "Bathrooms", shared_bath: "Shared bathroom", superhost: "Superhost" };

  Promise.all([fetch("data.json").then(function (r) { return r.json(); }), fetch("model.json").then(function (r) { return r.json(); })])
    .then(function (res) { render(res[0], res[1]); })
    .catch(function (e) { document.querySelector("main").insertAdjacentHTML("afterbegin", '<div class="card">Could not load data: ' + e + "</div>"); });

  function render(data, model) {
    renderKpis(data);
    renderMap(data.map);
    renderDistricts(data.districts);
    renderHist(data.price_hist);
    renderRooms(data.room_types);
    renderLicence(data.licence, data.kpis);
    renderEstimator(model);
    renderModel(data.model);
  }

  function renderKpis(d) {
    var k = d.kpis;
    $("#snapshot").textContent = d.snapshot;
    $("#k-listings-inline").textContent = fmt(k.listings);
    var items = [
      [fmt(k.listings), "active priced listings"],
      [euro(k.median_price), "median price / night"],
      [k.pct_entire + "%", "are entire homes"],
      [k.pct_multi_host + "%", "run by multi-listing hosts"],
      ["+" + k.superhost_price_premium + "%", "superhost price premium"],
    ];
    $("#kpis").innerHTML = items.map(function (i) { return '<div class="kpi"><b>' + i[0] + "</b><span>" + i[1] + "</span></div>"; }).join("");
  }

  // ---------- colour scale (light → brand red) ----------
  function scale(v, min, max) {
    var t = Math.max(0, Math.min(1, (v - min) / (max - min)));
    var a = [255, 236, 214], b = [196, 30, 58];
    var c = a.map(function (x, i) { return Math.round(x + (b[i] - x) * t); });
    return "rgb(" + c.join(",") + ")";
  }

  function renderMap(map) {
    var svg = $("#map-svg"), tip = $("#tooltip");
    svg.setAttribute("viewBox", "0 0 " + map.width + " " + map.height);
    var priced = map.shapes.filter(function (s) { return s.median_price != null; });
    var prices = priced.map(function (s) { return s.median_price; }).sort(function (a, b) { return a - b; });
    var min = prices[Math.floor(prices.length * 0.05)], max = prices[Math.floor(prices.length * 0.95)];
    svg.innerHTML = map.shapes.map(function (s, i) {
      var fill = s.median_price == null ? "#e4e7ec" : scale(s.median_price, min, max);
      return '<path data-i="' + i + '" d="' + s.path + '" fill="' + fill + '"></path>';
    }).join("");
    svg.addEventListener("mousemove", function (e) {
      var i = e.target.getAttribute && e.target.getAttribute("data-i");
      if (i == null) { tip.style.opacity = 0; return; }
      var s = map.shapes[i], box = svg.parentNode.getBoundingClientRect();
      tip.innerHTML = "<b>" + s.name + "</b><br>" + s.district + "<br>" +
        (s.median_price != null ? "Median " + euro(s.median_price) + " · " : "") + fmt(s.listings) + " listings";
      tip.style.left = Math.min(e.clientX - box.left + 12, box.width - 200) + "px";
      tip.style.top = (e.clientY - box.top + 12) + "px";
      tip.style.opacity = 1;
    });
    svg.addEventListener("mouseleave", function () { tip.style.opacity = 0; });
    $("#legend").innerHTML = '<div class="legend-bar" style="background:linear-gradient(90deg,' + scale(min, min, max) + "," + scale((min + max) / 2, min, max) + "," + scale(max, min, max) + ')"></div><div class="legend-labels"><span>≤ ' + euro(min) + "</span><span>≥ " + euro(max) + "</span></div>";
    var big = priced.filter(function (s) { return s.listings >= 20; }).sort(function (a, b) { return b.median_price - a.median_price; });
    var li = function (s) { return "<li>" + s.name + "<span>" + euro(s.median_price) + "</span></li>"; };
    $("#top-hoods").innerHTML = big.slice(0, 5).map(li).join("");
    $("#low-hoods").innerHTML = big.slice(-5).reverse().map(li).join("");
  }

  function renderDistricts(districts) {
    var fmtFor = { median_price: euro, listings: fmt, avg_booked_nights: function (v) { return Math.round(v); }, pct_entire: function (v) { return Math.round(v) + "%"; } };
    function draw(metric) {
      var rows = districts.slice().sort(function (a, b) { return b[metric] - a[metric]; });
      var max = Math.max.apply(null, rows.map(function (r) { return r[metric]; }));
      $("#district-chart").innerHTML = rows.map(function (r) {
        return '<div class="bar-row"><span>' + r.district + '</span><div class="bar-track"><div class="bar-fill" style="width:' + (100 * r[metric] / max).toFixed(1) + '%"></div></div><span class="bar-val">' + fmtFor[metric](r[metric]) + "</span></div>";
      }).join("");
    }
    draw("median_price");
    document.querySelectorAll("#district-metric button").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.querySelectorAll("#district-metric button").forEach(function (b) { b.classList.remove("on"); });
        btn.classList.add("on");
        draw(btn.getAttribute("data-m"));
      });
    });
  }

  function renderHist(h) {
    var W = 520, H = 230, P = { l: 44, r: 10, t: 10, b: 34 };
    var n = h.counts.length, max = Math.max.apply(null, h.counts);
    var bw = (W - P.l - P.r) / n, y = function (v) { return H - P.b - (v / max) * (H - P.t - P.b); };
    var out = "";
    for (var g = 0; g <= 4; g++) {
      var v = Math.round(max * g / 4), yy = y(v);
      out += '<line x1="' + P.l + '" x2="' + (W - P.r) + '" y1="' + yy + '" y2="' + yy + '" stroke="#eef0f4"/><text x="' + (P.l - 6) + '" y="' + (yy + 4) + '" font-size="11" text-anchor="end" fill="#667085">' + v + "</text>";
    }
    h.counts.forEach(function (c, i) {
      out += '<rect x="' + (P.l + i * bw + 1) + '" y="' + y(c) + '" width="' + (bw - 2) + '" height="' + (H - P.b - y(c)) + '" rx="3" fill="#ff5a5f"><title>€' + h.bins[i] + "–" + h.bins[i + 1] + ": " + c + " listings</title></rect>";
      if (i % 5 === 0) out += '<text x="' + (P.l + i * bw) + '" y="' + (H - 14) + '" font-size="11" fill="#667085">€' + h.bins[i] + "</text>";
    });
    $("#hist").innerHTML = '<svg viewBox="0 0 ' + W + " " + H + '" width="100%">' + out + "</svg>";
  }

  function renderRooms(rooms) {
    var total = rooms.reduce(function (s, r) { return s + r.listings; }, 0);
    $("#rooms").innerHTML = rooms.map(function (r) {
      var pct = 100 * r.listings / total;
      return '<div class="bar-row" style="grid-template-columns:130px 1fr 110px"><span>' + r.room_type + '</span><div class="bar-track"><div class="bar-fill" style="width:' + Math.max(pct, 1).toFixed(1) + '%;background:linear-gradient(90deg,#2f6fed,#7aa5ff)"></div></div><span class="bar-val">' + pct.toFixed(1) + "% · " + euro(r.median_price) + "</span></div>";
    }).join("") + '<p class="small">Bar = share of listings · value = share · median price per night</p>';
  }

  function renderLicence(lic, k) {
    var html = "";
    Object.keys(lic).forEach(function (group) {
      html += '<div class="stack-label">' + group + '</div><div class="stack">';
      Object.keys(lic[group]).forEach(function (cat) {
        var v = lic[group][cat];
        if (v > 0) html += '<div style="width:' + v + "%;background:" + LIC_COLORS[cat] + '" title="' + cat + ": " + v + '%">' + (v >= 6 ? v + "%" : "") + "</div>";
      });
      html += "</div>";
    });
    html += '<div class="legend-row">' + Object.keys(LIC_COLORS).map(function (c) { return '<span><i style="background:' + LIC_COLORS[c] + '"></i>' + c + "</span>"; }).join("") + "</div>";
    $("#licence").innerHTML = html;
    $("#licence-insight").innerHTML = "💡 Only <b>" + k.pct_short_term_missing_licence + "%</b> of short-term listings show no registration or disclosure. Most listings without a number set a minimum stay of 30+ nights, which falls outside the short-term letting rules. Many hosts appear to use long minimum stays to stay compliant.";
  }

  function renderEstimator(model) {
    var form = $("#est-form");
    var opts = function (arr, sel) { return arr.map(function (v) { return "<option" + (v === sel ? " selected" : "") + ">" + v + "</option>"; }).join(""); };
    form.district.innerHTML = opts(model.categories.district, "Friedrichshain-Kreuzberg");
    form.room_type.innerHTML = opts(model.categories.room_type, "Entire home/apt");
    var outputs = { accommodates: "#o-acc", bedrooms: "#o-bed", bathrooms: "#o-bath", minimum_nights: "#o-min", amenities_count: "#o-am", review_score: "#o-rev" };
    var mae = model.metrics.test_mae_eur;
    function update() {
      var input = {
        district: form.district.value, room_type: form.room_type.value,
        accommodates: +form.accommodates.value, bedrooms: +form.bedrooms.value, bathrooms: +form.bathrooms.value,
        minimum_nights: +form.minimum_nights.value, amenities_count: +form.amenities_count.value, review_score: +form.review_score.value,
        shared_bath: form.shared_bath.checked, superhost: form.superhost.checked,
      };
      Object.keys(outputs).forEach(function (k) { $(outputs[k]).textContent = input[k]; });
      var p = window.predictPrice(model, input);
      $("#est-price").textContent = euro(p);
      $("#est-range").textContent = "Typical range: " + euro(p * 0.8) + " – " + euro(p * 1.25);
      $("#est-note").textContent = "Model accuracy on unseen listings: average error ≈ €" + Math.round(mae) + ". Estimates are a guide, not financial advice.";
    }
    form.addEventListener("input", update);
    update();
  }

  function renderModel(m) {
    var bestR2 = Math.max.apply(null, m.comparison.map(function (r) { return r.test_r2_log; }));
    $("#model-table").innerHTML = "<tr><th>Model</th><th>CV R²</th><th>Test R²</th><th>MAE</th><th>Median error</th></tr>" +
      m.comparison.map(function (r) {
        return '<tr class="' + (r.test_r2_log === bestR2 ? "best" : "") + '"><td>' + r.model + (r.test_r2_log === bestR2 ? " ✅" : "") + "</td><td>" + r.cv_r2_log.toFixed(3) + "</td><td>" + r.test_r2_log.toFixed(3) + "</td><td>" + euro(r.test_mae_eur) + "</td><td>" + euro(r.test_median_ae_eur) + "</td></tr>";
      }).join("");
    var max = m.importance[0].importance;
    $("#importance").innerHTML = m.importance.map(function (f) {
      return '<div class="bar-row" style="grid-template-columns:130px 1fr 50px"><span>' + (FEATURE_LABELS[f.feature] || f.feature) + '</span><div class="bar-track"><div class="bar-fill" style="width:' + Math.max(1, 100 * f.importance / max).toFixed(1) + '%;background:linear-gradient(90deg,#12a150,#5fd08f)"></div></div><span class="bar-val">' + f.importance.toFixed(2) + "</span></div>";
    }).join("");
  }
})();
