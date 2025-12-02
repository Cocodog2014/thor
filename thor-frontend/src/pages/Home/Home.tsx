// src/pages/Home/Home.tsx
import React, { useEffect, useMemo, useState } from "react";
import GlobalMarkets from "../GlobalMarkets/GlobalMarkets";
import TwoByThreeGridSortable from "../../components/Grid/TwoByThreeGridSortable";
import type { DashboardTile } from "../../components/Grid/TwoByThreeGrid";

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
  const tileMap = useMemo(() => new Map(BASE_TILES.map((tile) => [tile.id, tile])), []);

  const [tiles, setTiles] = useState<DashboardTile[]>(() => {
    if (typeof window === "undefined") return BASE_TILES;
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (!stored) return BASE_TILES;
      const storedIds: string[] = JSON.parse(stored);
      const ordered: DashboardTile[] = [];
      storedIds.forEach((id) => {
        const tile = tileMap.get(id);
        if (tile) ordered.push(tile);
      });
      const remaining = BASE_TILES.filter((tile) => !storedIds.includes(tile.id));
      return [...ordered, ...remaining];
    } catch {
      return BASE_TILES;
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(tiles.map((tile) => tile.id)));
    } catch {
      // Ignore storage failures (e.g., disabled storage)
    }
  }, [tiles]);

  return (
    <div className="home-screen">
      <main className="home-content">
        <TwoByThreeGridSortable tiles={tiles} onReorder={setTiles} />
      </main>
    </div>
  );
};

export default Home;
