import React from "react";
import TwoByTwoGridSortable from "../../../components/Grid2x2/TwoByTwoGridSortable";
import type { DashboardTile } from "../../../components/Grid2x3/TwoByThreeGrid";
import GlobalMarkets from "../../GlobalMarkets/GlobalMarkets";
import FutureRTD from "../FutureRTD/FutureRTD";
import MarketDashboard from "../Market/MarketDashboard";
import { useDragAndDropTiles } from "../../../hooks/DragAndDrop";
import "./FutureHome.css";

// Futures home now uses a 2×2 grid (second row twice as tall)
const FUTURE_TILES: DashboardTile[] = [
  {
    id: "slot-1",
    title: "Global Markets",
    children: <GlobalMarkets />,
  },
  {
    id: "slot-2",
    title: "Futures RTD",
    children: <FutureRTD />,
  },
  {
    id: "slot-3",
    title: "Market Sessions",
    children: <MarketDashboard />,
  },
  {
    id: "slot-4",
    title: "Add Widget",
    hint: "Drop any futures widget here",
  },
];

const STORAGE_KEY = "thor.futures.tiles.order.v2";

const FutureHome: React.FC = () => {
  const { tiles, setTiles } = useDragAndDropTiles(FUTURE_TILES, { storageKey: STORAGE_KEY });

  return (
    <div className="future-screen">
      <main className="future-content">
        <TwoByTwoGridSortable tiles={tiles} onReorder={setTiles} />
      </main>
    </div>
  );
};

export default FutureHome;

