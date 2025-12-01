import React from "react";
import TwoByThreeGrid from "../../../components/Grid/TwoByThreeGrid";
import type { DashboardTile } from "../../../components/Grid/TwoByThreeGrid";
// No local CSS; layout handled by shared grid styles

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
  return <TwoByThreeGrid tiles={FUTURE_TILES} />;
};

export default FutureHome;

