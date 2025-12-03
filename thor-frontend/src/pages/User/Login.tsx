import React, { useState, useEffect } from "react";
import "./Login.css";
import ThorTradingImage from "../../assets/ThorTrading 16_9.png";

const Login: React.FC = () => {
  const [showSplash, setShowSplash] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setShowSplash(false);
    }, 4000); // 4 seconds splash duration
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="login-page">
      {/* Splash Card */}
      {showSplash && (
        <div className="splash-screen">
          <div className="splash-overlay"></div>
          <div className="splash-card">
            <h1>⚡ THOR’S WAR ROOM ⚡</h1>
            <p>Activating Neural Trading Systems...</p>
          </div>
        </div>
      )}

      {/* Login Form (revealed after splash) */}
      {!showSplash && (
        <div className="login-card-wrapper">
          <div className="login-card">
            <h2>Sign In</h2>
            <form>
              <input type="email" placeholder="Email" required />
              <input type="password" placeholder="Password" required />
              <button type="submit">Login</button>
            </form>
            <p>
              Don’t have an account? <a href="/register">Create one</a>
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default Login;
