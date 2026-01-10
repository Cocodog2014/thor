export { default } from './TwoByThreeGridComponent';
export type { DashboardTile } from './TwoByThreeGridComponent';

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
