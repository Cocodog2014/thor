import React, { useState } from "react";
import TwoByThreeGridSortable from "../../components/Grid/TwoByThreeGridSortable";
import type { DashboardTile } from "../../components/Grid/TwoByThreeGridSortable";
import GlobalMarkets from "../GlobalMarkets/GlobalMarkets";

const INITIAL_TILES: DashboardTile[] = [
  { id: "global", title: "Global Market", children: <GlobalMarkets /> },
  { id: "l1", title: "L1 Cards", hint: "Realtime futures quotes" },
  { id: "orders", title: "Open Orders" },
  { id: "positions", title: "Positions" },
  { id: "risk", title: "Risk Monitor" },
  { id: "system", title: "System Status" },
];

const HomeSortableDemo: React.FC = () => {
  const [tiles, setTiles] = useState<DashboardTile[]>(INITIAL_TILES);
  return (
    <div className="home-screen">
      <main className="home-content">
        <TwoByThreeGridSortable tiles={tiles} onReorder={setTiles} />
      </main>
    </div>
  );
};

export default HomeSortableDemo;