"""Quick WebSocket connectivity test.

Run this in browser DevTools console after starting the server:

const ws = new WebSocket("ws://127.0.0.1:8000/ws/");
ws.onmessage = (e) => console.log("📨 WS message:", JSON.parse(e.data));
ws.onopen = () => console.log("✅ WS connected");
ws.onerror = (e) => console.log("❌ WS error", e);
ws.onclose = () => console.log("🔌 WS closed");

Expected: You should see heartbeat messages every 30 seconds
"""
print(__doc__)
