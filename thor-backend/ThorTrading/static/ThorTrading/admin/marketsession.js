(function () {
    function setStickyOffset() {
        var header = document.getElementById("header");
        var offset = header ? header.offsetHeight : 0;
        document.documentElement.style.setProperty("--marketsession-sticky-top", (offset || 52) + "px");
    }

    function enableTopScrollbar(results, table) {
        var topScroll = document.querySelector(".marketsession-top-scroll");
        if (!topScroll) {
            topScroll = document.createElement("div");
            topScroll.className = "marketsession-top-scroll is-hidden";
            var spacer = document.createElement("div");
            spacer.className = "marketsession-top-scroll-spacer";
            topScroll.appendChild(spacer);
            results.parentNode.insertBefore(topScroll, results);
        }

        var spacerDiv = topScroll.querySelector(".marketsession-top-scroll-spacer");

        function syncWidths() {
            spacerDiv.style.width = table.scrollWidth + "px";
        }

        syncWidths();

        topScroll.classList.remove("is-hidden");

        var isSyncing = false;
        function syncScroll(source, target) {
            if (isSyncing) {
                return;
            }
            isSyncing = true;
            target.scrollLeft = source.scrollLeft;
            window.requestAnimationFrame(function () {
                isSyncing = false;
            });
        }

        topScroll.addEventListener("scroll", function () {
            syncScroll(topScroll, results);
        });

        results.addEventListener("scroll", function () {
            syncScroll(results, topScroll);
        });

        if (window.ResizeObserver) {
            var observer = new ResizeObserver(syncWidths);
            observer.observe(table);
        } else {
            window.addEventListener("resize", syncWidths);
        }
    }

    function enableRowHighlighting(table) {
        // Add highlight checkboxes to each row
        var tbody = table.querySelector("tbody");
        if (!tbody) return;

        var rows = tbody.querySelectorAll("tr");
        rows.forEach(function(row) {
            // Skip if already has highlight cell
            if (row.querySelector(".highlight-cell")) return;

            var cell = document.createElement("td");
            cell.className = "highlight-cell";
            
            var checkbox = document.createElement("input");
            checkbox.type = "checkbox";
            checkbox.className = "row-highlight-checkbox";
            checkbox.title = "Highlight this row";
            
            checkbox.addEventListener("change", function() {
                if (this.checked) {
                    row.classList.add("highlighted-row");
                } else {
                    row.classList.remove("highlighted-row");
                }
            });
            
            cell.appendChild(checkbox);
            row.insertBefore(cell, row.firstChild);
        });

        // Add header cell for the highlight column
        var thead = table.querySelector("thead tr");
        if (thead && !thead.querySelector(".highlight-header")) {
            var headerCell = document.createElement("th");
            headerCell.className = "highlight-header";
            headerCell.innerHTML = "📌";
            headerCell.title = "Highlight rows";
            thead.insertBefore(headerCell, thead.firstChild);
        }

        // Add row hover effect for easier tracking
        rows.forEach(function(row) {
            row.addEventListener("mouseenter", function() {
                if (!this.classList.contains("highlighted-row")) {
                    this.classList.add("hover-highlight");
                }
            });
            row.addEventListener("mouseleave", function() {
                this.classList.remove("hover-highlight");
            });
        });
    }

    document.addEventListener("DOMContentLoaded", function () {
        setStickyOffset();

        var results = document.querySelector("#changelist-form .results");
        if (!results) {
            return;
        }

        var table = results.querySelector("table");
        if (!table) {
            return;
        }

        // Always enable top scrollbar for horizontal scrolling
        enableTopScrollbar(results, table);
        
        // Enable row highlighting
        enableRowHighlighting(table);
    });

    window.addEventListener("resize", setStickyOffset);
})();
