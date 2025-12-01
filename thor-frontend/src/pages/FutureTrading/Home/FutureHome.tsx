import React from "react";
import TwoByThreeGrid from "../../../components/Grid/TwoByThreeGrid";
import type { DashboardTile } from "../../../components/Grid/TwoByThreeGrid";
import "./FutureHome.css";

// Blank 2×3 grid for Futures Home
const FUTURE_TILES: DashboardTile[] = [
  { id: "slot-1", title: "" },
  { id: "slot-2", title: "" },
  { id: "slot-3", title: "" },
  { id: "slot-4", title: "" },
  { id: "slot-5", title: "" },
  { id: "slot-6", title: "" },
];

const FutureHome: React.FC = () => {
  return (
    <div className="future-screen">
      <main className="future-content">
        <TwoByThreeGrid tiles={FUTURE_TILES} />
      </main>
    </div>
  );
};

export default FutureHome;

