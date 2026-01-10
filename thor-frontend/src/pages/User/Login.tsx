import React, { useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import WarRoomBanner from "./WarRoomBanner";
import "./Login.css";
import ThorTradingImage from "../../assets/ThorTrading 16-9.png";

const Login: React.FC = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  const redirectTarget = useMemo(() => {
    const params = new URLSearchParams(location.search);
    const next = params.get("next");
    // Default landing page after login
    return next && next.startsWith("/") ? next : "/app/home";
  }, [location.search]);

  const handleLogin = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email || !password) {
      toast.error("Please enter valid credentials.");
      return;
    }

    try {
      setLoading(true);
      const { data } = await api.post("/users/login/", { email, password });

      const accessToken = data?.access;
      const refreshToken = data?.refresh;

      if (!accessToken) {
        throw new Error("Missing access token in response");
      }

      login(accessToken, refreshToken ?? null);

      toast.success("Welcome back, commander.");
      navigate(redirectTarget, { replace: true });
    } catch (error: unknown) {
      const responseData = (error as { response?: { data?: unknown } }).response?.data as
        | {
            detail?: string;
            message?: string;
            non_field_errors?: string[];
            email?: string[];
            password?: string[];
          }
        | undefined;

      const message =
        responseData?.detail ||
        responseData?.message ||
        responseData?.non_field_errors?.[0] ||
        responseData?.email?.[0] ||
        responseData?.password?.[0] ||
        (error instanceof Error ? error.message : undefined) ||
        "Unable to log in. Please verify your credentials.";

      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      {/* Background */}
      <div
        className="background"
        style={{ backgroundImage: `url(${ThorTradingImage})` }}
      ></div>

      <WarRoomBanner />

      {/* Login Form */}
      <div className="login-wrapper">
        <div className="login-card">
          <h2>Activate War Console</h2>
          <form onSubmit={handleLogin}>
            <input
              name="email"
              type="email"
              placeholder="Email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={loading}
              required
            />
            <input
              name="password"
              type="password"
              placeholder="Password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={loading}
              required
            />
            <button type="submit" disabled={loading}>
              {loading ? "Activating…" : "Activate"}
            </button>
          </form>
          <p>
            Don't have a weapon?{" "}
            <a className="weapon-link" href="/auth/register">
              Create one
            </a>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;
