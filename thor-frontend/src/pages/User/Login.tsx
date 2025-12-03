import React, { useState, useEffect } from "react";
import "./Login.css";
import ThorTradingImage from "../../assets/ThorTrading 16_9.png";

const Login: React.FC = () => {
  const [showLogin, setShowLogin] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setShowLogin(true), 1000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="login-container">
      {/* Background Image */}
      <div
        className="background"
        style={{ backgroundImage: `url(${ThorTradingImage})` }}
      ></div>

      {/* Splash Overlay */}
      <div className={`splash ${showLogin ? "fade-out" : ""}`}>
        <div className="splash-card">
          <h1>⚡ THOR’S WAR ROOM ⚡</h1>
          <p>Activating Neural Trading Systems...</p>
        </div>
      </div>

      {/* Login Form */}
      <div className={`login-wrapper ${showLogin ? "fade-in" : ""}`}>
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
    </div>
  );
};

export default Login;
