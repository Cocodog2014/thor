# Grid App Development Guidelines

## Overview
Apps rendered inside the `TwoByThreeGrid` tiles must follow specific width and height constraints to ensure proper display and scrolling behavior.

## Container Rules

### Width Constraints (REQUIRED)
```css
.your-app-container {
  width: 100%;           /* Must fill tile width */
  max-width: 100%;       /* Never exceed tile width */
  box-sizing: border-box; /* Include padding in width calculation */
  overflow-x: hidden;    /* Prevent horizontal scroll */
}
```

**Why:** The tile has a fixed width based on the grid layout. Apps MUST respect this width and never cause horizontal scrolling.

### Height Behavior (AUTOMATIC)
```css
.your-app-container {
  height: 100%;          /* Fill available tile height */
  min-height: 0;         /* Allow flex shrinking */
  overflow-y: auto;      /* Enable vertical scroll if content is too tall */
}
```

**Why:** The `.tbt-body` container handles vertical overflow automatically. Apps that are taller than the tile will scroll vertically inside the tile.

## Grid Component Behavior

The `TwoByThreeGrid` component provides:
- **`.tbt-body`**: Scrollable container with `overflow-y: auto` and `overflow-x: hidden`
- **Width enforcement**: Tiles are sized by the 2-column grid, apps must fit within
- **Height flexibility**: Apps can be any height - scroll appears automatically

## App Structure Pattern

```tsx
const YourApp: React.FC = () => {
  return (
    <div className="your-app-container">
      {/* Header (optional, sticky) */}
      <header className="your-app-header">
        Fixed header content
      </header>
      
      {/* Scrollable content */}
      <div className="your-app-content">
        Long content that may need to scroll...
      </div>
    </div>
  );
};
```

```css
.your-app-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 100%;
  height: 100%;
  min-height: 0;
  box-sizing: border-box;
  overflow: hidden; /* Container itself doesn't scroll */
}

.your-app-content {
  flex: 1;
  overflow-y: auto;   /* Content area scrolls */
  overflow-x: hidden; /* Never horizontal scroll */
}
```

## Real Example: GlobalMarkets

```css
.timezone-container {
  width: 100%;           /* Fill tile width */
  height: 100%;          /* Fill tile height */
  max-width: 100%;       /* Never exceed tile width */
  box-sizing: border-box;
  overflow: hidden;
}

.markets-table-container {
  flex: 1;
  overflow-y: auto;      /* Table scrolls vertically */
  overflow-x: hidden;    /* Table never scrolls horizontally */
}

.markets-table {
  width: 100%;           /* Table fits container width */
  table-layout: fixed;   /* Fixed layout prevents width overflow */
}
```

## Common Mistakes to Avoid

❌ **DON'T** set fixed pixel widths on your container
```css
.bad-container {
  width: 800px; /* Will overflow tile! */
}
```

❌ **DON'T** use `overflow-x: auto` or `overflow-x: scroll`
```css
.bad-container {
  overflow-x: auto; /* Causes horizontal scrollbar! */
}
```

❌ **DON'T** forget `box-sizing: border-box`
```css
.bad-container {
  width: 100%;
  padding: 20px; /* Without box-sizing, this overflows! */
}
```

✅ **DO** use percentage/flex-based widths
```css
.good-container {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
}
```

✅ **DO** enable vertical scrolling for tall content
```css
.good-content {
  overflow-y: auto;
  overflow-x: hidden;
}
```

## Summary

1. **Width**: Always `100%`, never exceed, use `box-sizing: border-box`
2. **Height**: Use `100%` to fill tile, `overflow-y: auto` for scrolling
3. **Horizontal overflow**: Always `hidden`, never `auto` or `scroll`
4. **Vertical overflow**: Use `auto` on scrollable content areas
5. **Grid handles**: Scroll behavior automatically in `.tbt-body`
