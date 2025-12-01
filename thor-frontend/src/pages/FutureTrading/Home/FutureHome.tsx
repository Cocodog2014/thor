import React from "react";
import GlobalMarkets from "../../GlobalMarkets/GlobalMarkets";
import TwoByThreeGrid from "../../../components/Grid/TwoByThreeGrid";
import type { DashboardTile } from "../../../components/Grid/TwoByThreeGrid";

const HOME_TILES: DashboardTile[] = [
  { 
    id: "global", 
    title: "", 
    slotLabel: "", 
    children: <GlobalMarkets /> 
  },
  { id: "pl", title: "RTD", slotLabel: "Slot 2", hint: "Real Time Data" },
  { id: "news", title: "Schwab Network / News", slotLabel: "Slot 3", hint: "Video / headlines" },
  { id: "watchlist", title: "Heat Map / Watchlist", slotLabel: "Slot 4", hint: "Top movers, sectors" },
  { id: "events", title: "Today's Events", slotLabel: "Slot 5", hint: "Economic calendar / orders" },
  { id: "system", title: "System Status", slotLabel: "Slot 6", hint: "Feeds, jobs, alerts" },
];

const Home: React.FC = () => {
  return (
    <div className="home-screen">
      <main className="home-content">
        <TwoByThreeGrid tiles={HOME_TILES} />
      </main>
    </div>
  );
};

export default Home;

