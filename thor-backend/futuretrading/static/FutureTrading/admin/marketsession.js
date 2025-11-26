(function () {
    document.addEventListener("DOMContentLoaded", function () {
        var params = new URLSearchParams(window.location.search);
        var colset = params.get("colset") || "basic";
        if (colset !== "full") {
            return;
        }

        var results = document.querySelector("#changelist-form .results");
        if (!results) {
            return;
        }

        var table = results.querySelector("table");
        if (!table) {
            return;
        }

        var topScroll = document.createElement("div");
        topScroll.className = "marketsession-top-scroll";
        var spacer = document.createElement("div");
        spacer.className = "marketsession-top-scroll-spacer";
        topScroll.appendChild(spacer);
        results.parentNode.insertBefore(topScroll, results);

        function syncWidths() {
            spacer.style.width = table.scrollWidth + "px";
        }

        syncWidths();

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
    });
})();
