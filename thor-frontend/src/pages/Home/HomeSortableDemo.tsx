import React, { useEffect, useMemo, useState } from "react";
import TwoByThreeGridSortable from "../../components/Grid/TwoByThreeGridSortable";
import type { DashboardTile } from "../../components/Grid/TwoByThreeGrid";
import GlobalMarkets from "../GlobalMarkets/GlobalMarkets";

const INITIAL_TILES: DashboardTile[] = [
  { id: "global", title: "Global Market", children: <GlobalMarkets /> },
  { id: "l1", title: "L1 Cards", hint: "Realtime futures quotes" },
  { id: "orders", title: "Open Orders" },
  { id: "positions", title: "Positions" },
  { id: "risk", title: "Risk Monitor" },
  { id: "system", title: "System Status" },
];

const STORAGE_KEY = "thor.homeSortable.order";

const HomeSortableDemo: React.FC = () => {
  const tileMap = useMemo(() => new Map(INITIAL_TILES.map((tile) => [tile.id, tile])), []);

  const [tiles, setTiles] = useState<DashboardTile[]>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (!stored) return INITIAL_TILES;
      const storedIds: string[] = JSON.parse(stored);
      const ordered: DashboardTile[] = [];
      storedIds.forEach((id) => {
        const tile = tileMap.get(id);
        if (tile) ordered.push(tile);
      });
      const remaining = INITIAL_TILES.filter((tile) => !storedIds.includes(tile.id));
      return [...ordered, ...remaining];
    } catch {
      return INITIAL_TILES;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(tiles.map((tile) => tile.id)));
    } catch {
      // Ignore storage errors (private mode, etc.)
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

export default HomeSortableDemo;