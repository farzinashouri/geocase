/* Filtering and sorting for the generated catalog compare page.
 *
 * Progressive enhancement only: generate_catalog_pages.py renders the complete
 * table server-side, so the page stays fully readable with JavaScript off. No
 * external library -- the docs build ships no bundler and adding one for a
 * search box would be a poor trade.
 */

(function () {
  "use strict";

  function init() {
    var table = document.getElementById("gc-compare-table");
    if (!table) {
      return;
    }

    var body = table.tBodies[0];
    var rows = Array.prototype.slice.call(body.rows);
    var search = document.getElementById("gc-compare-search");
    var count = document.getElementById("gc-compare-count");
    var selects = Array.prototype.slice.call(
      document.querySelectorAll(".gc-compare-filter"),
    );

    // Rows keyed by case id, so a footprint on the map can find its row.
    var byId = {};
    rows.forEach(function (row) {
      byId[row.dataset.caseId] = row;
    });

    // Set of case ids when the reader has clicked a map cluster; null when the
    // map is not filtering. Kept out of the selects so "clear" is one action.
    var mapFilter = null;
    var chip = null;

    function apply() {
      var term = search ? search.value.trim().toLowerCase() : "";
      var shown = 0;

      rows.forEach(function (row) {
        var visible = true;

        if (term && row.dataset.search.indexOf(term) === -1) {
          visible = false;
        }

        if (visible && mapFilter && !mapFilter[row.dataset.caseId]) {
          visible = false;
        }

        if (visible) {
          visible = selects.every(function (select) {
            return (
              !select.value || row.dataset[select.dataset.field] === select.value
            );
          });
        }

        row.hidden = !visible;
        if (visible) {
          shown += 1;
        }
      });

      if (count) {
        count.textContent =
          "Showing " + shown + " of " + rows.length + " cases";
      }
      renderChip();
    }

    function renderChip() {
      if (!count) {
        return;
      }
      if (!mapFilter) {
        if (chip) {
          chip.parentNode.removeChild(chip);
          chip = null;
        }
        return;
      }
      if (!chip) {
        chip = document.createElement("span");
        chip.className = "gc-map-filter-chip";
        var clear = document.createElement("button");
        clear.type = "button";
        clear.textContent = "clear";
        clear.addEventListener("click", function () {
          mapFilter = null;
          apply();
        });
        chip.appendChild(document.createTextNode(""));
        chip.appendChild(clear);
        count.parentNode.insertBefore(chip, count.nextSibling);
      }
      var total = 0;
      for (var id in mapFilter) {
        if (Object.prototype.hasOwnProperty.call(mapFilter, id)) {
          total += 1;
        }
      }
      chip.firstChild.nodeValue =
        "Showing " + total + " case" + (total === 1 ? "" : "s") + " from the map";
    }

    function highlight(ids, on) {
      ids.forEach(function (id) {
        var row = byId[id];
        if (row) {
          row.classList.toggle("gc-row-highlight", on);
        }
      });
    }

    // Bind the world maps to the table. Progressive enhancement: the maps are
    // complete, readable SVG on their own, and the interactive affordances are
    // set from here rather than baked into the generated markup so the
    // committed page text stays small.
    Array.prototype.slice
      .call(document.querySelectorAll(".gc-worldmap [data-case-id], .gc-worldmap [data-case-ids]"))
      .forEach(function (node) {
        var ids = (
          node.dataset.caseIds || node.dataset.caseId || ""
        )
          .split(/\s+/)
          .filter(Boolean);
        if (!ids.length) {
          return;
        }

        node.tabIndex = 0;
        node.setAttribute("role", "button");

        function enter() {
          highlight(ids, true);
        }
        function leave() {
          highlight(ids, false);
        }

        node.addEventListener("mouseenter", enter);
        node.addEventListener("focus", enter);
        node.addEventListener("mouseleave", leave);
        node.addEventListener("blur", leave);

        function activate() {
          if (ids.length === 1) {
            var row = byId[ids[0]];
            if (row) {
              row.hidden = false;
              row.scrollIntoView({ block: "center" });
              highlight(ids, true);
            }
            return;
          }
          mapFilter = {};
          ids.forEach(function (id) {
            mapFilter[id] = true;
          });
          apply();
        }

        node.addEventListener("click", activate);
        node.addEventListener("keydown", function (event) {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            activate();
          }
        });
      });

    // Column index 0 is the preview, which has nothing to sort on; the header
    // cells carrying data-sort start at index 1.
    function sortKey(row, index) {
      var cell = row.cells[index];
      return cell ? cell.textContent.trim().toLowerCase() : "";
    }

    Array.prototype.slice
      .call(table.querySelectorAll("th[data-sort]"))
      .forEach(function (header) {
        header.tabIndex = 0;
        header.setAttribute("role", "button");

        function sort() {
          var index = header.cellIndex;
          var ascending = header.dataset.direction !== "asc";

          table.querySelectorAll("th[data-sort]").forEach(function (other) {
            if (other !== header) {
              delete other.dataset.direction;
              other.removeAttribute("aria-sort");
            }
          });
          header.dataset.direction = ascending ? "asc" : "desc";
          header.setAttribute(
            "aria-sort",
            ascending ? "ascending" : "descending",
          );

          var sorted = rows.slice().sort(function (a, b) {
            var left = sortKey(a, index);
            var right = sortKey(b, index);
            if (left === right) {
              // Ties fall back to the case id so the order is deterministic.
              return a.dataset.caseId.localeCompare(b.dataset.caseId);
            }
            return ascending
              ? left.localeCompare(right)
              : right.localeCompare(left);
          });

          sorted.forEach(function (row) {
            body.appendChild(row);
          });
        }

        header.addEventListener("click", sort);
        header.addEventListener("keydown", function (event) {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            sort();
          }
        });
      });

    if (search) {
      search.addEventListener("input", apply);
    }
    selects.forEach(function (select) {
      select.addEventListener("change", apply);
    });

    apply();
  }

  // Material for MkDocs swaps page content without a full reload, so binding
  // to DOMContentLoaded alone would leave the table inert after any in-site
  // navigation.
  if (window.document$ && typeof window.document$.subscribe === "function") {
    window.document$.subscribe(init);
  } else if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
