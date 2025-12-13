// src/pages/Home/Home.tsx
import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import GlobalMarkets from "../GlobalMarkets/GlobalMarkets";
import TwoByThreeGridSortable from "../../components/Grid2x3/TwoByThreeGridSortable";
import type { DashboardTile } from "../../components/Grid2x3/TwoByThreeGrid";
import { useDragAndDropTiles } from "../../hooks/DragAndDrop";
import CommanderWelcomeModal from "../../components/modals/CommanderWelcome/CommanderWelcomeModal";
import { HOME_WELCOME_DISMISSED_KEY } from "../../constants/storageKeys";

type TileCTAProps = {
  description: string;
  buttonLabel: string;
  onClick?: () => void;
  disabled?: boolean;
  helperText?: string;
};

const TileCTA: React.FC<TileCTAProps> = ({ description, buttonLabel, onClick, disabled, helperText }) => (
  <div className="home-tile-cta">
    <p>{description}</p>
    {helperText && <small>{helperText}</small>}
    <button type="button" onClick={onClick} disabled={disabled}>
      {buttonLabel}
    </button>
  </div>
);

const BASE_TILES: DashboardTile[] = [
  { id: "global", title: "Global Markets", slotLabel: "Markets" },
  { id: "activity", title: "Activity & Positions", slotLabel: "Positions" },
  { id: "statement", title: "Account Statement", slotLabel: "Statements" },
  { id: "news", title: "Schwab Network / News", slotLabel: "News" },
  { id: "system", title: "System Status", slotLabel: "System" },
];

const STORAGE_KEY = "thor.home.tiles.order";

const Home: React.FC = () => {
  const [showWelcome, setShowWelcome] = useState<boolean>(false);
  const [hasLoadedPreference, setHasLoadedPreference] = useState(false);
  const { tiles, setTiles } = useDragAndDropTiles(BASE_TILES, { storageKey: STORAGE_KEY });
  const navigate = useNavigate();

  useEffect(() => {
    try {
      const stored = sessionStorage.getItem(HOME_WELCOME_DISMISSED_KEY);
      setShowWelcome(stored !== "true");
    } catch {
      setShowWelcome(true);
    } finally {
      setHasLoadedPreference(true);
    }
  }, []);

  const dismissWelcome = () => {
    setShowWelcome(false);
    try {
      sessionStorage.setItem(HOME_WELCOME_DISMISSED_KEY, "true");
    } catch {
      /* ignore sessionStorage restrictions */
    }
    navigate("/app/home");
  };

  const enhancedTiles = useMemo(() => {
    return tiles.map((tile) => {
      if (tile.id === "global") {
        return { ...tile, children: <GlobalMarkets /> };
      }

      if (tile.id === "activity") {
        return {
          ...tile,
          children: (
            <TileCTA
              description="Monitor balances, buying power, positions, and today's fills."
              buttonLabel="Open Activity & Positions"
              onClick={() => navigate("/app/activity")}
            />
          ),
        };
      }

      if (tile.id === "statement") {
        return {
          ...tile,
          children: (
            <TileCTA
              description="Run a date-range account statement with trades, cash, and P&L."
              buttonLabel="Open Account Statement"
              onClick={() => navigate("/app/account-statement")}
            />
          ),
        };
      }

      return tile;
    });
  }, [tiles, navigate]);

  return (
    <div className="home-screen">
      <main className="home-content">
        <CommanderWelcomeModal open={hasLoadedPreference && showWelcome} onDismiss={dismissWelcome} />
        <TwoByThreeGridSortable tiles={enhancedTiles} onReorder={setTiles} />
      </main>
    </div>
  );
};

export default Home;
