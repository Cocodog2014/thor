// src/components/Grid2x3/TwoByThreeGrid.tsx
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

const COLUMN_COUNT = 2;
const ROW_COUNT = 3;
const MAX_TILES = COLUMN_COUNT * ROW_COUNT;

const TwoByThreeGrid: React.FC<TwoByThreeGridProps> = ({ tiles }) => {
  const trimmedTiles = tiles.slice(0, MAX_TILES);
  const paddedTiles = trimmedTiles.concat(
    Array.from({ length: MAX_TILES - trimmedTiles.length }, (_, idx) => ({
      id: `empty-${idx}`,
      title: "",
    }))
  );

  return (
    <div className="tbt-grid">
      {paddedTiles.map((tile, idx) => (
          <section
            key={tile.id}
            className={`tbt-tile tbt-tile-${idx + 1}`}
            data-row={Math.floor(idx / COLUMN_COUNT) + 1}
            data-column={(idx % COLUMN_COUNT) + 1}
          >
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
