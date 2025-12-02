// src/components/Grid2x2/TwoByTwoGrid.tsx
import React from "react";
import type { DashboardTile } from "../Grid2x3/TwoByThreeGrid";
import "./TwoByTwoGrid.css";

type TwoByTwoGridProps = {
  tiles: DashboardTile[];
};

const COLUMN_COUNT = 2;
const ROW_COUNT = 2;
const MAX_TILES = COLUMN_COUNT * ROW_COUNT;

const TwoByTwoGrid: React.FC<TwoByTwoGridProps> = ({ tiles }) => {
  const trimmedTiles = tiles.slice(0, MAX_TILES);
  const paddedTiles = trimmedTiles.concat(
    Array.from({ length: MAX_TILES - trimmedTiles.length }, (_, idx) => ({
      id: `empty-${idx}`,
      title: "",
    }))
  );

  return (
    <div className="g22-grid">
      {paddedTiles.map((tile, idx) => (
        <section
          key={tile.id}
          className={`g22-tile g22-tile-${idx + 1}`}
          data-row={Math.floor(idx / COLUMN_COUNT) + 1}
          data-column={(idx % COLUMN_COUNT) + 1}
        >
          <header className="g22-header">
            <span className="g22-title">{tile.title}</span>
            <span className="g22-slot">{tile.slotLabel ?? `Slot ${idx + 1}`}</span>
          </header>

          <div className="g22-body">
            {tile.children ? (
              tile.children
            ) : tile.hint ? (
              <p className="g22-hint">{tile.hint}</p>
            ) : null}
          </div>
        </section>
      ))}
    </div>
  );
};

export default TwoByTwoGrid;
