import React from "react";
import "./WarRoomBanner.css";

const ROTATING_LINES = [
  "You command your army of AI.",
  "Unleash your storm upon the world.",
  "Command your AI army.",
  "An army of AI warriors at your command."
];

const WarRoomBanner: React.FC = () => {
  const currentLine = ROTATING_LINES[0];

  return (
    <div className="war-banner">
      <div className="war-banner-card">
        <h1>⚡ THOR'S WAR ROOM ⚡</h1>
        <p className="banner-subtitle">Activating AI Battle System...</p>
        <div className="banner-rotator" aria-live="polite">
          <span>{currentLine}</span>
        </div>
      </div>
    </div>
  );
};

export default WarRoomBanner;
