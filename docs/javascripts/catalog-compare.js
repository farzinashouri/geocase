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

    function apply() {
      var term = search ? search.value.trim().toLowerCase() : "";
      var shown = 0;

      rows.forEach(function (row) {
        var visible = true;

        if (term && row.dataset.search.indexOf(term) === -1) {
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
    }

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
