# GlobalBanner Component

The **GlobalBanner** is the black, Thinkorswim-style banner that sits directly under the blue `GlobalHeader` AppBar. It is responsible for:

- Showing **connection status** to the quotes engine.
- Displaying and allowing selection of the **active trading account**.
- Showing **buying power / net liquidity** for the selected account.
- Rendering top-level **navigation tabs** (`Home`, `Trade`, `Futures`, `Global`) and optional child tabs.
- Providing quick links (email, Messages, Support, Chat Rooms, Setup).

---

## Files

- **Orchestrator:** `GlobalBanner.tsx`
- **Subcomponents:**
  - `TopRow.tsx` – connection status, account dropdown, quick links
  - `BalanceRow.tsx` – Option/Stock buying power + Net Liq
  - `TabsRow.tsx` – parent & child navigation tabs
- **Shared types:** `bannerTypes.ts`
- **Styles:** `GlobalBanner.css`

---

## Responsibilities & Behavior

### 1. Connection Status

The banner pings the quotes API on an interval to decide whether to show **Connected** or **Disconnected**.

In `GlobalBanner.tsx`:

```ts
useEffect(() => {
  let isMounted = true;

  const checkConnection = async () => {
    try {
      const response = await fetch(
        '/api/quotes/latest?consumer=futures_trading',
        { cache: 'no-store' }, // fetch option, not a custom header
      );

      if (!response.ok) {
        throw new Error(`Status ${response.status}`);
      }

      const data: { rows?: unknown[] } = await response.json();
      const rows = Array.isArray(data?.rows) ? data.rows : [];
      const hasLiveData = rows.length > 0;

      if (!isMounted) return;

      if (hasLiveData) {
        setConnectionStatus('connected');
        setLastUpdate(new Date().toLocaleTimeString());
      } else {
        setConnectionStatus('disconnected');
      }
    } catch (err) {
      if (!isMounted) return;
      console.error('GlobalBanner: error checking connection', err);
      setConnectionStatus('disconnected');
    }
  };

  checkConnection();
  const interval = setInterval(checkConnection, 5000);

  return () => {
    isMounted = false;
    clearInterval(interval);
  };
}, []);
