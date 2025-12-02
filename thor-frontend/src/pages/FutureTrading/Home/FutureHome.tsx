import React from "react";
import TwoByThreeGridSortable from "../../../components/Grid/TwoByThreeGridSortable";
import type { DashboardTile } from "../../../components/Grid/TwoByThreeGrid";
import { useDragAndDropTiles } from "../../../hooks/DragAndDrop";
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

const STORAGE_KEY = "thor.futures.tiles.order";

const FutureHome: React.FC = () => {
  const { tiles, setTiles } = useDragAndDropTiles(FUTURE_TILES, { storageKey: STORAGE_KEY });

  return (
    <div className="future-screen">
      <main className="future-content">
        <TwoByThreeGridSortable tiles={tiles} onReorder={setTiles} />
      </main>
    </div>
  );
};

export default FutureHome;

