import React, { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import api from "../../services/api";
import { useAuth } from "../../context/AuthContext";
import "./Login.css";

const Login: React.FC = () => {
  const [showSplash, setShowSplash] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setShowSplash(false);
    }, 4000); // 4 seconds splash duration
    return () => window.clearTimeout(timer);
  }, []);

  const redirectTarget = useMemo(() => {
    const params = new URLSearchParams(location.search);
    const next = params.get("next");
    return next && next.startsWith("/") ? next : "/app/home";
  }, [location.search]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email || !password) {
      toast.error("Email and password are required");
      return;
    }

    try {
      setLoading(true);
      const { data } = await api.post("/users/login/", {
        email,
        password,
      });

      const accessToken = data?.access;
      const refreshToken = data?.refresh;

      if (!accessToken) {
        throw new Error("Missing access token in response");
      }

      login(accessToken);

      if (refreshToken) {
        try {
          localStorage.setItem("thor_refresh_token", refreshToken);
        } catch {
          // Ignore storage access errors (private mode, etc.)
        }
      }

      toast.success("Welcome back, commander.");
      navigate(redirectTarget, { replace: true });
    } catch (error: any) {
      const message =
        error?.response?.data?.detail ||
        error?.response?.data?.message ||
        error?.message ||
        "Unable to log in. Please verify your credentials.";
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      {/* Splash Card */}
      {showSplash && (
        <div className="splash-screen">
          <div className="splash-overlay"></div>
          <div className="splash-card">
            <h1>⚡ THOR'S WAR ROOM ⚡</h1>
            <p>Activating Neural Trading Systems...</p>
          </div>
        </div>
      )}

      {/* Login Form (revealed after splash) */}
      {!showSplash && (
        <div className="login-card-wrapper fade-in">
          <div className="login-card">
            <h2>Sign In</h2>
            <form onSubmit={handleSubmit}>
              <input
                type="email"
                name="email"
                placeholder="Email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                disabled={loading}
                required
              />
              <input
                type="password"
                name="password"
                placeholder="Password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={loading}
                required
              />
              <button type="submit" disabled={loading}>
                {loading ? "Logging in…" : "Login"}
              </button>
            </form>
            <p>
              Don't have an account? <a href="/auth/register">Create one</a>
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default Login;
