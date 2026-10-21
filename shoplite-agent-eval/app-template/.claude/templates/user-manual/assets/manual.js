// Builds the navigation tree and runs the search box of every user-manual page from site-data.js, so a new
// page only needs its own content plus one entry in site-data.js. The language switch and the search box
// are plain HTML in each page (they work without this script); this file fills the navigation and the results.
// Plain script (no modules, no fetch): the manual must work when opened straight from the file system.
(function () {
  "use strict";

  var site = window.MANUAL;
  if (!site || !Array.isArray(site.pages)) {
    return;
  }
  var labels = site.labels || {};
  var current = decodeURIComponent(location.pathname.split("/").pop() || "index.html");
  var MAX_NAV_DEPTH = 6;

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (name) { node.setAttribute(name, attrs[name]); });
    if (text) {
      node.textContent = text;
    }
    return node;
  }

  function childrenOf(parent) {
    return site.pages.filter(function (p) { return (p.parent || "") === parent && p.file !== parent; });
  }

  function buildList(parent, depth) {
    var items = childrenOf(parent);
    if (!items.length || depth > MAX_NAV_DEPTH) {
      return null;
    }
    var list = el("ul");
    items.forEach(function (page) {
      var item = el("li");
      var link = el("a", { href: page.file }, page.title);
      if (page.file === current) {
        link.setAttribute("aria-current", "page");
      }
      item.appendChild(link);
      var sub = buildList(page.file, depth + 1);
      if (sub) {
        item.appendChild(sub);
      }
      list.appendChild(item);
    });
    return list;
  }

  function buildNav() {
    var nav = document.getElementById("manual-nav");
    if (!nav) {
      return;
    }
    nav.setAttribute("aria-label", labels.navigation || "");
    var tree = buildList("", 0);
    if (tree) {
      nav.appendChild(tree);
    }
  }

  function normalize(text) {
    return (text || "").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "");
  }

  function matches(page, words) {
    var haystack = normalize([page.title, page.keywords, page.summary].join(" "));
    return words.every(function (w) { return haystack.indexOf(w) !== -1; });
  }

  function wireSearch() {
    var box = document.getElementById("manual-search-box");
    var results = document.getElementById("manual-search-results");
    if (!box || !results) {
      return;
    }
    box.addEventListener("input", function () {
      results.textContent = "";
      var words = normalize(box.value).split(/\s+/).filter(Boolean);
      if (!words.length) {
        return;
      }
      var found = site.pages.filter(function (p) { return matches(p, words); });
      if (!found.length) {
        results.appendChild(el("li", {}, labels.noResults || ""));
        return;
      }
      found.forEach(function (page) {
        var item = el("li");
        item.appendChild(el("a", { href: page.file }, page.title));
        if (page.summary) {
          item.appendChild(el("p", {}, page.summary));
        }
        results.appendChild(item);
      });
    });
  }

  wireSearch();
  buildNav();
}());
