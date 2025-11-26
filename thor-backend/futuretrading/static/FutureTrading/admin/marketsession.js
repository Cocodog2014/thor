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

        var params = new URLSearchParams(window.location.search);
        var colset = params.get("colset") || "basic";
        if (colset === "full") {
            enableTopScrollbar(results, table);
        }
    });

    window.addEventListener("resize", setStickyOffset);
})();
