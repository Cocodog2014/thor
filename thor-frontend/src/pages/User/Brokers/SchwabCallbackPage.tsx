import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import api from "../../../services/api";

export default function SchwabCallbackPage() {
  const loc = useLocation();
  const nav = useNavigate();
  const [msg, setMsg] = useState("Finishing Schwab connection…");

  useEffect(() => {
    (async () => {
      try {
        await api.get(`schwab/oauth/callback/${loc.search}`);
        setMsg("Connected! Redirecting…");
        setTimeout(() => nav("/app/user/brokers?connected=1", { replace: true }), 600);
      } catch {
        setMsg("Schwab connect failed. Please try again.");
      }
    })();
  }, [loc.search, nav]);

  return (
    <div style={{ padding: 16 }}>
      <div style={{ border: "1px solid rgba(255,255,255,0.15)", padding: 16, borderRadius: 10 }}>
        {msg}
      </div>
    </div>
  );
}
