// TabsRow.tsx
import React from 'react';
import type { ParentTab, ChildTab } from './bannerTypes';

interface TabsRowProps {
  parentTabs: ParentTab[];
  childTabsByParent: Record<string, ChildTab[]>;
  activeParentKey: string;
  onParentClick: (tabKey: string, tabPath: string) => void;
  onChildClick: (parentKey: string, path: string) => void;
  locationPathname: string;
}

const TabsRow: React.FC<TabsRowProps> = ({
  parentTabs,
  childTabsByParent,
  activeParentKey,
  onParentClick,
  onChildClick,
  locationPathname,
}) => {
  const childTabs = childTabsByParent[activeParentKey] ?? [];

  return (
    <>
      {/* Row 3 parent tabs */}
      <nav className="global-banner-tabs home-nav">
        {parentTabs.map((tab) => {
          const active = activeParentKey === tab.key;
          return (
            <button
              key={tab.label}
              type="button"
              onClick={() => onParentClick(tab.key, tab.path)}
              className={`home-nav-button${active ? ' active' : ''}`}
            >
              {tab.label}
            </button>
          );
        })}
      </nav>

      {/* Row 4 child tabs */}
      {childTabs.length > 0 && (
        <nav className="global-banner-subtabs">
          {childTabs.map((child) => {
            const active = locationPathname === child.path;
            return (
              <button
                key={child.label}
                type="button"
                onClick={() => onChildClick(activeParentKey, child.path)}
                className={`home-nav-button-child${active ? ' active' : ''}`}
              >
                {child.label}
              </button>
            );
          })}
        </nav>
      )}
    </>
  );
};

export default TabsRow;
