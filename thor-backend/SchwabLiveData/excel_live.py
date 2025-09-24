from __future__ import annotations

import threading
import time
import re
from typing import Dict, Any, List, Optional
import os
from datetime import datetime, timezone

try:
    import xlwings as xw  # venv install required
except Exception:
    xw = None

_SYMBOL_ALIASES = {
    "RT": "RTY",
    "30YBOND": "ZB",
    "30YRBOND": "ZB",  # accommodate common variant
}
_CANONICAL11 = ["/YM", "/ES", "/NQ", "RTY", "CL", "SI", "HG", "GC", "VX", "DX", "ZB"]


def _canon_symbol(s: str) -> str:
    s = (s or "").strip().upper().lstrip("/")
    s = _SYMBOL_ALIASES.get(s, s)
    if s in {"YM", "ES", "NQ"}:
        return f"/{s}"
    return s


def _parse_frac_32(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    txt = str(v).strip().replace(",", "")
    m = re.match(r"^(\d+)'(\d+)$", txt)
    if m:
        return float(m.group(1)) + float(m.group(2)) / 32.0
    try:
        return float(txt)
    except Exception:
        return None


def _num(v: Any) -> Optional[float]:
    return _parse_frac_32(v)


class ExcelLiveProvider:
    """
    Polls an open Excel workbook via COM (xlwings) on a background thread,
    normalizes the selected range, and serves the latest cached snapshot.
    """

    def __init__(
        self,
        file_path: str,
        sheet_name: str = "Futures",
        range_address: str = "A1:M20",
        poll_ms: int = 200,
        require_open: bool = False,
    ):
        if xw is None:
            raise RuntimeError("xlwings not installed in venv (pip install xlwings pywin32).")
        self.file_path = file_path
        self.sheet_name = sheet_name
        self.range_address = range_address
        self.poll_ms = poll_ms
        self.require_open = require_open

        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._snapshot: Dict[str, Any] = {"rows": [], "meta": {"ts": None}}
        self._iteration_count: int = 0
        self._last_error: Optional[str] = None
        
        # Auto-start the polling thread
        self.start()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="ExcelLivePoller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _loop(self) -> None:
        # Attach to an existing Excel instance; open the book if needed.
        book = None
        sheet = None
        try:
            # When require_open is True, do not open files implicitly; attach to an open workbook only
            if self.require_open:
                app = xw.apps.active if getattr(xw.apps, "count", 0) > 0 else None
                if not app:
                    self._last_error = f"No Excel application found; require_open=True prevents opening {self.file_path}"
                    return
                filename = os.path.basename(self.file_path).lower()
                for b in app.books:
                    try:
                        if os.path.samefile(b.fullname, self.file_path) or b.name.lower() == filename:
                            book = b
                            break
                    except Exception:
                        # Fall back to name-only match for unsaved books
                        if b.name.lower() == filename:
                            book = b
                            break
                if not book:
                    self._last_error = f"Excel Live: Workbook not open: {self.file_path}"
                    return
                sheet = book.sheets[self.sheet_name]
            else:
                # xw.Book(path) will bind to the open book or open it if not already open.
                book = xw.Book(self.file_path)
                sheet = book.sheets[self.sheet_name]
        except Exception:
            # Try to bind by filename among currently open books
            try:
                app = xw.apps.active if getattr(xw.apps, "count", 0) > 0 else None
                if not app:
                    self._last_error = f"Excel Live: No Excel application found, cannot attach to {self.file_path}"
                    return
                filename = self.file_path.split("\\")[-1].lower()
                for b in app.books:
                    if b.name.lower() == filename:
                        book = b
                        break
                if not book:
                    self._last_error = f"Excel Live: Book {filename} not found in open Excel books"
                    return
                sheet = book.sheets[self.sheet_name]
            except Exception as e:
                self._last_error = f"Excel Live: Failed to attach to Excel application: {e}"
                return

        while not self._stop.is_set():
            try:
                grid = sheet.range(self.range_address).value  # 2D list (header + rows)
                rows = self._normalize_grid(grid)
                with self._lock:
                    self._snapshot = {
                        "rows": rows,
                        "meta": {
                            "ts": datetime.now(timezone.utc).isoformat(),
                            "provider_type": "excel_live",
                            "excel_file": book.fullname,
                            "sheet": self.sheet_name,
                            "range": self.range_address,
                        },
                    }
                self._iteration_count += 1
                self._last_error = None
            except Exception:
                # Swallow read errors and keep polling; status endpoint can expose details if needed
                pass
            time.sleep(self.poll_ms / 1000.0)

    def _normalize_grid(self, grid: List[List[Any]]) -> List[Dict[str, Any]]:
        if not grid or not isinstance(grid, list) or not grid[0]:
            return []
        headers = [("" if h is None else str(h)).strip() for h in grid[0]]
        if not headers[0]:
            headers[0] = "symbol"

        idx = {h.lower(): i for i, h in enumerate(headers)}

        def col(name: str) -> Optional[int]:
            for key in (name, name.replace(" ", ""), name.replace("_", "")):
                i = idx.get(key.lower())
                if i is not None:
                    return i
            return None

        c_sym = col("symbol")
        c_last = col("last") or col("price")
        c_bid = col("bid")
        c_ask = col("ask")
        c_open = col("open")
        c_close = col("close") or col("previous_close")
        c_high = col("world high") or col("high")
        c_low = col("world low") or col("low")
        c_vol = col("volume") or col("vol")
        c_bsz = col("bidsize") or col("bid_size")
        c_asz = col("asksize") or col("ask_size")
        c_net = col("netchange") or col("change")
        c_pct = col("perc") or col("changepercent")

        out: List[Dict[str, Any]] = []
        for r in grid[1:]:
            if not r:
                continue
            # Symbol
            sym_raw = ""
            if c_sym is not None and c_sym < len(r) and r[c_sym] is not None:
                sym_raw = str(r[c_sym]).strip()
            sym = _canon_symbol(sym_raw)
            if not sym:
                continue

            last = _num(r[c_last]) if (c_last is not None and c_last < len(r)) else None
            bid = _num(r[c_bid]) if (c_bid is not None and c_bid < len(r)) else None
            ask = _num(r[c_ask]) if (c_ask is not None and c_ask < len(r)) else None
            openp = _num(r[c_open]) if (c_open is not None and c_open < len(r)) else None
            prev = _num(r[c_close]) if (c_close is not None and c_close < len(r)) else None
            high = _num(r[c_high]) if (c_high is not None and c_high < len(r)) else None
            low = _num(r[c_low]) if (c_low is not None and c_low < len(r)) else None
            vol = _num(r[c_vol]) if (c_vol is not None and c_vol < len(r)) else None
            bsz = _num(r[c_bsz]) if (c_bsz is not None and c_bsz < len(r)) else None
            asz = _num(r[c_asz]) if (c_asz is not None and c_asz < len(r)) else None
            net = _num(r[c_net]) if (c_net is not None and c_net < len(r)) else None
            pct = _num(r[c_pct]) if (c_pct is not None and c_pct < len(r)) else None

            row = {
                "instrument": {
                    "symbol": sym,
                    "name": sym,
                    "display_precision": 2,
                    "is_active": True,
                    "sort_order": _CANONICAL11.index(sym) if sym in _CANONICAL11 else 999,
                },
                "price": last,
                "bid": bid,
                "ask": ask,
                "bid_size": bsz,
                "ask_size": asz,
                "open_price": openp,
                "previous_close": prev,
                "high_price": high,
                "low_price": low,
                "volume": vol,
                "change": net,
                "change_percent": pct,
                "vwap": None,
                "market_status": "OPEN",
                "extended_data": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            out.append(row)

        out.sort(key=lambda x: x["instrument"]["sort_order"])
        return out

    def get_latest_quotes(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Return the latest cached snapshot. `symbols` is accepted for API
        compatibility with other providers but is ignored because the Excel
        range already determines which instruments are present.
        """
        with self._lock:
            # Return a shallow copy so callers can’t mutate internal state
            return dict(self._snapshot)

    # --- Health and metadata helpers to align with BaseProvider expectations ---
    def health_check(self) -> Dict[str, Any]:
        try:
            connected = bool(self._snapshot.get("meta", {}).get("ts"))
        except Exception:
            connected = False
        return {
            "provider": "excel_live",
            "connected": connected,
            "excel_file": self.file_path,
            "sheet": self.sheet_name,
            "range": self.range_address,
            "poll_ms": self.poll_ms,
            "last_update": self._snapshot.get("meta", {}).get("ts"),
            "iteration_count": self._iteration_count,
            "last_error": self._last_error,
        }

    def get_provider_name(self) -> str:
        return "Excel Live Provider (xlwings)"