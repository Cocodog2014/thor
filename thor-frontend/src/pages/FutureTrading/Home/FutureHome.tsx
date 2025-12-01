import React from 'react';
import TwoByThreeGrid from '../../../components/Grid/TwoByThreeGrid';
import type { DashboardTile } from '../../../components/Grid/TwoByThreeGrid';
import FutureRTD from '../FutureRTD/FutureRTD';
import './FutureHome.css';

const FUTURES_TILES: DashboardTile[] = [
  { 
    id: "rtd", 
    title: "", 
    slotLabel: "", 
    children: <FutureRTD /> 
  },
  { id: "analysis", title: "Technical Analysis", slotLabel: "Slot 2", hint: "Charts & indicators" },
  { id: "positions", title: "Open Positions", slotLabel: "Slot 3", hint: "Active futures contracts" },
  { id: "alerts", title: "Price Alerts", slotLabel: "Slot 4", hint: "Threshold notifications" },
  { id: "history", title: "Trade History", slotLabel: "Slot 5", hint: "Past executions" },
  { id: "research", title: "Market Research", slotLabel: "Slot 6", hint: "Reports & analysis" },
];

const FutureHome: React.FC = () => {
  return (
    <div className="future-home-screen">
      <main className="future-home-content">
        <TwoByThreeGrid tiles={FUTURES_TILES} />
      </main>
    </div>
  );
};

export default FutureHome;
