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

    // --- the map tooltip ---------------------------------------------------
    //
    // The SVG <title> the generator emits stays in place as the no-JS
    // fallback, but it is a poor primary affordance: a native tooltip waits
    // about a second, cannot wrap, and truncates exactly the long cluster
    // lists that most need reading. This replaces it while hovering.

    //: Ids listed in full before the tooltip switches to a count. Eight fits
    //: the tooltip's width without turning a 36-case cluster into a wall.
    var MAX_LISTED_IDS = 8;

    var tooltip = document.createElement("div");
    tooltip.className = "gc-map-tooltip";
    tooltip.hidden = true;
    // aria-hidden: the same text is already on the element's <title>, which is
    // what a screen reader reads. Announcing it twice helps nobody.
    tooltip.setAttribute("aria-hidden", "true");
    document.body.appendChild(tooltip);

    function tooltipText(ids, isCluster) {
      var head = document.createElement("span");
      head.className = "gc-map-tooltip-head";

      var body = document.createElement("span");
      body.className = "gc-map-tooltip-ids";

      if (isCluster) {
        head.textContent =
          ids.length + " case" + (ids.length === 1 ? "" : "s") + " here";
        body.textContent = ids.slice(0, MAX_LISTED_IDS).join(", ");
        if (ids.length > MAX_LISTED_IDS) {
          body.textContent +=
            ", and " + (ids.length - MAX_LISTED_IDS) + " more";
        }
      } else {
        head.textContent = ids[0];
        body.textContent = "";
      }

      tooltip.textContent = "";
      tooltip.appendChild(head);
      if (body.textContent) {
        tooltip.appendChild(body);
      }
      return tooltip;
    }

    function positionTooltip(event) {
      // Offset from the cursor, then flipped back inside the viewport when the
      // tooltip would overhang -- otherwise a marker near the right edge shows
      // its tooltip half off-screen, which is where the long ones live.
      var pad = 12;
      var rect = tooltip.getBoundingClientRect();
      var x = event.clientX + pad;
      var y = event.clientY + pad;

      if (x + rect.width > window.innerWidth - pad) {
        x = event.clientX - rect.width - pad;
      }
      if (y + rect.height > window.innerHeight - pad) {
        y = event.clientY - rect.height - pad;
      }
      tooltip.style.left = Math.max(pad, x) + "px";
      tooltip.style.top = Math.max(pad, y) + "px";
    }

    function showTooltip(ids, isCluster, hint, event) {
      tooltipText(ids, isCluster);
      if (hint) {
        var note = document.createElement("span");
        note.className = "gc-map-tooltip-hint";
        note.textContent = hint;
        tooltip.appendChild(note);
      }
      tooltip.hidden = false;
      positionTooltip(event);
    }

    function hideTooltip() {
      tooltip.hidden = true;
    }

    // --- footprints: hover only --------------------------------------------
    //
    // A footprint names its case and highlights its row. It is deliberately
    // NOT clickable: the mixed affordance (help cursor plus a click that
    // jumped the page) is what made the maps feel unpredictable.

    Array.prototype.slice
      .call(document.querySelectorAll(".gc-worldmap [data-case-id]"))
      .forEach(function (node) {
        var ids = (node.dataset.caseId || "").split(/\s+/).filter(Boolean);
        if (!ids.length) {
          return;
        }

        node.addEventListener("mouseenter", function (event) {
          highlight(ids, true);
          showTooltip(ids, false, "", event);
        });
        node.addEventListener("mousemove", positionTooltip);
        node.addEventListener("mouseleave", function () {
          highlight(ids, false);
          hideTooltip();
        });
      });

    // --- clusters: hover and click -----------------------------------------
    //
    // CLICKABLE-START -- clusters are the only pressable thing on the map.
    // Filtering the table is the one action that pays for a click here:
    // a 36-case marker cannot be read any other way.

    Array.prototype.slice
      .call(document.querySelectorAll(".gc-worldmap [data-case-ids]"))
      .forEach(function (node) {
        var ids = (node.dataset.caseIds || "").split(/\s+/).filter(Boolean);
        if (!ids.length) {
          return;
        }

        var isCluster = ids.length > 1;
        // A one-case marker has nothing to filter down to, so it stays a
        // hover target and never claims to be a button.
        if (isCluster) {
          node.tabIndex = 0;
          node.setAttribute("role", "button");
        } else {
          node.style.cursor = "default";
        }

        var hint = isCluster ? "Click to filter the table to these cases" : "";

        node.addEventListener("mouseenter", function (event) {
          highlight(ids, true);
          showTooltip(ids, isCluster, hint, event);
        });
        node.addEventListener("mousemove", positionTooltip);
        node.addEventListener("mouseleave", function () {
          highlight(ids, false);
          hideTooltip();
        });

        if (!isCluster) {
          return;
        }

        node.addEventListener("focus", function () {
          highlight(ids, true);
        });
        node.addEventListener("blur", function () {
          highlight(ids, false);
          hideTooltip();
        });

        function activate() {
          mapFilter = {};
          ids.forEach(function (id) {
            mapFilter[id] = true;
          });
          hideTooltip();
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
    // CLICKABLE-END

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
