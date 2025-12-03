import React, { useEffect, useState } from "react";
import "./WarRoomBanner.css";

const ROTATION_INTERVAL_MS = 2000;
const ROTATING_LINES = [
  "You command your army of AI.",
  "Unleash your storm upon the world.",
  "Command your AI army.",
  "An army of AI warriors at your command."
];

const WarRoomBanner: React.FC = () => {
  const [lineIndex, setLineIndex] = useState(0);
  const [messageKey, setMessageKey] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => {
      setLineIndex((prev) => (prev + 1) % ROTATING_LINES.length);
      setMessageKey((prev) => prev + 1);
    }, ROTATION_INTERVAL_MS);

    return () => window.clearInterval(id);
  }, []);

  const currentLine = ROTATING_LINES[lineIndex];

  return (
    <div className="war-banner">
      <div className="war-banner-card">
        <h1>⚡ THOR'S WAR ROOM ⚡</h1>
        <p className="banner-subtitle">Activating AI Battle System...</p>
        <div className="banner-rotator" aria-live="polite">
          <span key={messageKey}>{currentLine}</span>
        </div>
      </div>
    </div>
  );
};

export default WarRoomBanner;
