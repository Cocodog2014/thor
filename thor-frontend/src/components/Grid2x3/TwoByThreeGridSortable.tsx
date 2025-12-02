// src/components/Grid2x3/TwoByThreeGridSortable.tsx
import React, { useMemo } from "react";
import {
  DndContext,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  arrayMove,
  rectSortingStrategy,
  sortableKeyboardCoordinates,
} from "@dnd-kit/sortable";
import type { DragEndEvent } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import "./TwoByThreeGrid.css";
import type { DashboardTile } from "./TwoByThreeGrid";

type TwoByThreeGridSortableProps = {
  tiles: DashboardTile[];
  onReorder?: (next: DashboardTile[]) => void;
};

const COLUMN_COUNT = 2;
const ROW_COUNT = 3;
const MAX_TILES = COLUMN_COUNT * ROW_COUNT;

function SortableTile({ tile, index }: { tile: DashboardTile; index: number }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: tile.id });

  const transformStyle = transform ? CSS.Transform.toString(transform) : undefined;

  return (
    <div
      ref={setNodeRef}
      style={{ transform: transformStyle, transition } as React.CSSProperties}
      className={`tbt-tile tbt-tile-${index + 1}${isDragging ? ' tbt-tile-dragging' : ''}`}
      data-row={Math.floor(index / COLUMN_COUNT) + 1}
      data-column={(index % COLUMN_COUNT) + 1}
    >
      <header className="tbt-header">
        <button
          className="tbt-drag-handle"
          aria-label="Drag tile"
          {...attributes}
          {...listeners}
        >
          ⋮⋮
        </button>
        <span className="tbt-title">{tile.title}</span>
        <span className="tbt-slot">{tile.slotLabel ?? `Slot ${index + 1}`}</span>
      </header>

      <div className="tbt-body">
        {tile.children ? (
          tile.children
        ) : tile.hint ? (
          <p className="tbt-hint">{tile.hint}</p>
        ) : null}
      </div>
    </div>
  );
}

const TwoByThreeGridSortable: React.FC<TwoByThreeGridSortableProps> = ({ tiles, onReorder }) => {
  const trimmedTiles = tiles.slice(0, MAX_TILES);
  const paddedTiles = useMemo(
    () =>
      trimmedTiles.concat(
        Array.from({ length: MAX_TILES - trimmedTiles.length }, (_, idx) => ({
          id: `empty-${idx}`,
          title: "",
        }))
      ),
    [trimmedTiles]
  );

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id || !onReorder) return;

    const ids = trimmedTiles.map((t) => t.id);
    const oldIndex = ids.indexOf(String(active.id));
    const newIndex = ids.indexOf(String(over.id));
    if (oldIndex === -1 || newIndex === -1) return;
    const nextOrder = arrayMove(trimmedTiles, oldIndex, newIndex);
    onReorder(nextOrder);
  };

  // Only make non-empty tiles sortable
  const sortableIds = useMemo(
    () => trimmedTiles.map((t) => t.id),
    [trimmedTiles]
  );

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <SortableContext items={sortableIds} strategy={rectSortingStrategy}>
        <div className="tbt-grid">
          {paddedTiles.map((tile, idx) =>
            tile.id.startsWith("empty-") ? (
              <div
                key={tile.id}
                className={`tbt-tile tbt-tile-${idx + 1}`}
                data-row={Math.floor(idx / COLUMN_COUNT) + 1}
                data-column={(idx % COLUMN_COUNT) + 1}
              />
            ) : (
              <SortableTile key={tile.id} tile={tile} index={idx} />
            )
          )}
        </div>
      </SortableContext>
    </DndContext>
  );
};

export default TwoByThreeGridSortable;