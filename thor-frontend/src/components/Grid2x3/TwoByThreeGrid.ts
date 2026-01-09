/**
 * DashboardTile - Type definitions and behavior for Home dashboard tiles
 */

export interface DashboardTile {
  id: string;
  title: string;
  content: React.ReactNode;
  order: number;
  size?: 'small' | 'large';
}

export interface TilePosition {
  id: string;
  order: number;
}

/**
 * Grid layout configuration
 * 2x3 layout = 2 columns, 3 rows max before scrolling
 */
export const GRID_CONFIG = {
  columns: 2,
  rows: 3,
  maxTiles: 6,
  gapSize: 16,
} as const;

/**
 * Helper to validate tile order
 */
export const isValidTileOrder = (tiles: DashboardTile[]): boolean => {
  return tiles.every((tile, idx) => tile.order === idx);
};

/**
 * Helper to reorder tiles after drag-drop
 */
export const reorderTiles = (
  tiles: DashboardTile[],
  fromIndex: number,
  toIndex: number
): DashboardTile[] => {
  const result = Array.from(tiles);
  const [removed] = result.splice(fromIndex, 1);
  result.splice(toIndex, 0, removed);
  return result.map((tile, idx) => ({ ...tile, order: idx }));
};
