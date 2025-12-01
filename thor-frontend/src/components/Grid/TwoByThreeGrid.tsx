// src/components/Grid/TwoByThreeGrid.tsx
import React from "react";
import "./TwoByThreeGrid.css";

export type DashboardTile = {
  id: string;
  title: string;
  slotLabel?: string;
  hint?: string;
  children?: React.ReactNode;
};

type TwoByThreeGridProps = {
  tiles: DashboardTile[];
};

const TwoByThreeGrid: React.FC<TwoByThreeGridProps> = ({ tiles }) => {
  return (
    <div className="tbt-grid">
      {tiles.slice(0, 6).map((tile, idx) => (
        <section key={tile.id} className={`tbt-tile tbt-tile-${idx + 1}`}>
          <header className="tbt-header">
            <span className="tbt-title">{tile.title}</span>
            <span className="tbt-slot">{tile.slotLabel ?? `Slot ${idx + 1}`}</span>
          </header>

          <div className="tbt-body">
            {tile.children ? (
              tile.children
            ) : tile.hint ? (
              <p className="tbt-hint">{tile.hint}</p>
            ) : null}
          </div>
        </section>
      ))}
    </div>
  );
};

export default TwoByThreeGrid;
