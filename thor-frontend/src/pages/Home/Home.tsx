// src/pages/Home/Home.tsx
import React from "react";
import GlobalMarkets from "../GlobalMarkets/GlobalMarkets";
import TwoByThreeGridSortable from "../../components/Grid/TwoByThreeGridSortable";
import type { DashboardTile } from "../../components/Grid/TwoByThreeGrid";
import { useDragAndDropTiles } from "../../hooks/DragAndDrop";

const BASE_TILES: DashboardTile[] = [
  {
    id: "global",
    title: "",
    slotLabel: "",
    children: <GlobalMarkets />,
  },
  { id: "pl", title: "RTD", slotLabel: "Slot 2", hint: "Real Time Data" },
  { id: "news", title: "Schwab Network / News", slotLabel: "Slot 3", hint: "Video / headlines" },
  { id: "watchlist", title: "Heat Map / Watchlist", slotLabel: "Slot 4", hint: "Top movers, sectors" },
  { id: "events", title: "Today's Events", slotLabel: "Slot 5", hint: "Economic calendar / orders" },
  { id: "system", title: "System Status", slotLabel: "Slot 6", hint: "Feeds, jobs, alerts" },
];

const STORAGE_KEY = "thor.home.tiles.order";

const Home: React.FC = () => {
  const { tiles, setTiles } = useDragAndDropTiles(BASE_TILES, { storageKey: STORAGE_KEY });

  return (
    <div className="home-screen">
      <main className="home-content">
        <TwoByThreeGridSortable tiles={tiles} onReorder={setTiles} />
      </main>
    </div>
  );
};

export default Home;
