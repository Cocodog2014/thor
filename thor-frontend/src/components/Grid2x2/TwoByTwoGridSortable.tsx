// src/components/Grid2x2/TwoByTwoGridSortable.tsx
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
import type { DashboardTile } from "../Grid2x3/TwoByThreeGrid";
import "./TwoByTwoGrid.css";

type TwoByTwoGridSortableProps = {
  tiles: DashboardTile[];
  onReorder?: (next: DashboardTile[]) => void;
};

const COLUMN_COUNT = 2;
const ROW_COUNT = 2;
const MAX_TILES = COLUMN_COUNT * ROW_COUNT;

function SortableTile({ tile, index }: { tile: DashboardTile; index: number }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: tile.id });

  const transformStyle = transform ? CSS.Transform.toString(transform) : undefined;

  return (
    <div
      ref={setNodeRef}
      style={{ transform: transformStyle, transition } as React.CSSProperties}
      className={`g22-tile g22-tile-${index + 1}${isDragging ? " g22-tile-dragging" : ""}`}
      data-row={Math.floor(index / COLUMN_COUNT) + 1}
      data-column={(index % COLUMN_COUNT) + 1}
    >
      <header className="g22-header">
        <button className="g22-drag-handle" aria-label="Drag tile" {...attributes} {...listeners}>
          ⋮⋮
        </button>
        <span className="g22-title">{tile.title}</span>
        <span className="g22-slot">{tile.slotLabel ?? `Slot ${index + 1}`}</span>
      </header>

      <div className="g22-body">
        {tile.children ? (
          tile.children
        ) : tile.hint ? (
          <p className="g22-hint">{tile.hint}</p>
        ) : null}
      </div>
    </div>
  );
}

const TwoByTwoGridSortable: React.FC<TwoByTwoGridSortableProps> = ({ tiles, onReorder }) => {
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

  const sortableIds = useMemo(() => trimmedTiles.map((t) => t.id), [trimmedTiles]);

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <SortableContext items={sortableIds} strategy={rectSortingStrategy}>
        <div className="g22-grid">
          {paddedTiles.map((tile, idx) =>
            tile.id.startsWith("empty-") ? (
              <div
                key={tile.id}
                className={`g22-tile g22-tile-${idx + 1}`}
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

export default TwoByTwoGridSortable;
