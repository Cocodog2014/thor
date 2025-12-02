import { useCallback, useEffect, useMemo, useState } from 'react';
import type { DashboardTile } from '../components/Grid/TwoByThreeGrid';

type UseDragAndDropOptions = {
  /** Optional key for persisting tile order across reloads. */
  storageKey?: string;
};

const hasWindow = typeof window !== 'undefined';

function loadOrderFromStorage(
  storageKey: string | undefined,
  tileMap: Map<string, DashboardTile>,
  fallback: DashboardTile[]
): DashboardTile[] {
  if (!storageKey || !hasWindow) return fallback;

  try {
    const stored = window.localStorage.getItem(storageKey);
    if (!stored) return fallback;
    const storedIds: string[] = JSON.parse(stored);

    const ordered: DashboardTile[] = [];
    storedIds.forEach((id) => {
      const tile = tileMap.get(id);
      if (tile) ordered.push(tile);
    });

    const remaining = fallback.filter((tile) => !storedIds.includes(tile.id));
    return [...ordered, ...remaining];
  } catch {
    return fallback;
  }
}

export function useDragAndDropTiles(
  baseTiles: DashboardTile[],
  options?: UseDragAndDropOptions
) {
  const { storageKey } = options ?? {};

  const baseTileMap = useMemo(
    () => new Map(baseTiles.map((tile) => [tile.id, tile] as const)),
    [baseTiles]
  );

  const [tiles, setTiles] = useState<DashboardTile[]>(() =>
    loadOrderFromStorage(storageKey, baseTileMap, baseTiles)
  );

  useEffect(() => {
    setTiles((prev) => {
      const allowedIds = new Set(baseTiles.map((tile) => tile.id));
      const filtered = prev.filter((tile) => allowedIds.has(tile.id));
      const existingIds = new Set(filtered.map((tile) => tile.id));
      const missing = baseTiles.filter((tile) => !existingIds.has(tile.id));
      return [...filtered, ...missing];
    });
  }, [baseTiles]);

  useEffect(() => {
    if (!storageKey || !hasWindow) return;
    try {
      window.localStorage.setItem(storageKey, JSON.stringify(tiles.map((tile) => tile.id)));
    } catch {
      // Ignore storage failures (e.g., private mode)
    }
  }, [tiles, storageKey]);

  const resetTiles = useCallback(() => {
    if (storageKey && hasWindow) {
      try {
        window.localStorage.removeItem(storageKey);
      } catch {
        // Ignore storage failures
      }
    }
    setTiles(baseTiles);
  }, [baseTiles, storageKey]);

  return { tiles, setTiles, resetTiles };
}
