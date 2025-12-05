MarketSession System — Developer Reference

Last updated: December 2025

This document explains the architecture, purpose, and interactions of the Market Sessions front-end module used inside the Futures App. It is intended for ongoing development and future contributors.

📌 Overview

The MarketSession system renders real-time market session cards for each country in CONTROL_MARKETS.
Each card displays:

Live market session data

Intraday 1-minute snapshots

Futures baskets (TOTAL + individual futures)

Open / High / Low / Close deltas

Best-bid / best-ask

Weighted average for TOTAL

24h / 52-week statistics

Session-level meta data (volume, local date, signals, weights)

The module must remain high-performance, modular, and easy to maintain, even as the data structure grows.

📁 File Structure
/src/features/market/
│
├── MarketSessions.tsx
├── MarketSessionCard.tsx
│
├── marketSessionTypes.ts
├── marketSessionUtils.ts
├── useMarketSessions.ts
│
└── (optional future components)
    ├── TotalSessionCard.tsx
    ├── FutureSessionCard.tsx
    ├── SessionStatsTable.tsx

📘 File Responsibilities
1. MarketSessions.tsx

(Entry point / wrapper — small and clean)

Handles:

✔ Layout wrapper
✔ Inline CSS (intentionally scoped here)
✔ Section header
✔ Fetches session datasets via useMarketSessions()
✔ Delegates each session card to MarketSessionCard

Does NOT contain business logic or rendering logic anymore.
It must stay light.

2. MarketSessionCard.tsx

(The full card rendering logic for one country's session)

This file contains:

Data selection logic (latest rows, TOTAL vs individual future)

Market-open / pre-open hiding rules

Intraday snapshot rendering

Session summary grids

BBO layout (Bid/Ask)

Range delta cards

Select dropdown for choosing the future contract

Meta blocks (Entry price, Local Date, Weighted Avg)

Right-side stats panel (24h, 52w, session metrics)

All the big UI structures live here.

The card is controlled by props:

interface MarketSessionCardProps {
  controlMarket: ControlMarket;
  rows: any[];
  liveStatus?: any;
  intradaySnapshot?: any;
  selectedSymbol: string;
  onChangeFuture(symbol: string): void;
}


It is purely presentational and receives everything it needs from MarketSessions.tsx.

3. useMarketSessions.ts

(Data retrieval, state, and transformation)

This is the hook responsible for:

Data it fetches:

Global session dataset

Intraday 1m data

Live session status (open/close timers)

Grouping rows by country

Maintaining per-country selected future

State it exposes:
{
  liveStatus,
  intradayLatest,
  selected,
  setSelected,
  byCountry,
}

Notes:

This is the ONLY place that touches API URLs.

If the backend changes its endpoint structure, update this file.

4. marketSessionTypes.ts

(Constants + data definitions)

Exports:

✔ CONTROL_MARKETS

List of markets (Japan, China, India, USA, etc.) with labels, countries, and keys.

✔ FUTURE_OPTIONS

Dropdown futures list (TOTAL, ES, NQ, RTY, YM, CL, etc.)

✔ Optional field types

For example MarketRow, IntradaySnapshot, etc.

This file must contain no logic — only configuration.

5. marketSessionUtils.ts

(Formatting + calculation helpers)

Contains all shared utility functions:

formatNum, formatNumOrDash

formatSignedValue

formatPercentValue

parseNumericValue

getDeltaClass, getTriangleClass

buildPercentCell

normalizeCountry

formatIntradayValue

getSessionDateKey

isZero, isToday

Rules:

Pure functions only

No React imports

No API calls

Must remain stable and predictable

📊 Data Flow Summary
Step 1 — MarketSessions loads

Calls useMarketSessions(apiUrl)

Retrieves all session rows grouped by country

Retrieves intraday snapshots

Retrieves live session status

Step 2 — Render a card for each CONTROL_MARKET

Each card is rendered via:

<MarketSessionCard
   controlMarket={m}
   rows={rows}
   liveStatus={liveStatus[m.country]}
   intradaySnapshot={intradayLatest[m.key]}
   selectedSymbol={selected[m.key] || "TOTAL"}
   onChangeFuture={(symbol) => ... }
/>

Step 3 — The card renders the session

Based on:

Latest capture row

TOTAL vs individual future

Intraday snapshot availability

Session-open state + rules

Metric calculations from utils

🧩 Extension Guidelines
Adding a new country

Edit:

marketSessionTypes.ts
CONTROL_MARKETS

Adding a new future contract

Edit:

FUTURE_OPTIONS

Adding new metrics

Most should be added in:

MarketSessionCard.tsx (presentation)

marketSessionUtils.ts (calculation)

useMarketSessions.ts (if backend adds new fields)

Modifying styling

All styling currently lives in an inline <style> block inside MarketSessions.tsx.

This is intentional:

Prevents global CSS collisions

Ensures component-scoped theme behavior

Easy to move later into a dedicated CSS module

Splitting further

Cards can later be separated into:

TotalSessionCard.tsx

FutureSessionCard.tsx

RangeDeltaGroup.tsx

BBOCard.tsx

IntradayPanel.tsx

We already isolated ~70% of the logic; splitting again is easy.

⚠️ Important Rules
DO NOT put routing in MarketSession or MarketSessionCard

Routing belongs in:

App.tsx
FutureHome.tsx

DO NOT fetch data inside MarketSessionCard

It must stay pure and only render props.

DO NOT duplicate helper functions

Keep all formatting utilities inside marketSessionUtils.ts.

DO NOT pass unprocessed API results directly into a card

Always normalize inside the hook.

🏁 Summary

This module is now:

Modular

Maintainable

Performance-friendly

Easy to extend

Clean and readable

You can safely expand your futures system without letting any single file grow out of control again.

Absolutely — here is a full architecture package for your MarketSession system:

Data Flow Diagram

Component Flow Diagram

Dependency Map

Future Roadmap (How to keep it clean and scalable)

This will be the companion to your MarketSession.md.

📊 1. DATA FLOW DIAGRAM (API → Hook → UI)
                   ┌────────────────────────────┐
                   │   Backend (Django API)     │
                   │   /api/market-opens/latest │
                   │   /api/live_status/        │
                   │   /api/intraday/latest     │
                   └───────────────┬────────────┘
                                   │ JSON
                                   ▼
                 ┌─────────────────────────────────┐
                 │      useMarketSessions.ts       │
                 │---------------------------------│
                 │ - Polls backend every 1s        │
                 │ - Normalizes rows               │
                 │ - Groups data by country        │
                 │ - Determines session status     │
                 │ - Tracks selected future symbol │
                 └───────────────┬─────────────────┘
                                 │ Hook Output
                                 ▼
                    ┌──────────────────────┐
                    │  MarketSessions.tsx  │
                    │  (Session List View) │
                    └───────────┬──────────┘
                                │ For each control market
                                ▼
                 ┌──────────────────────────────────┐
                 │        MarketSessionCard.tsx      │
                 │  - TOTAL layout                   │
                 │  - Individual futures layout      │
                 │  - BBO Panel                      │
                 │  - Session stats grid             │
                 │  - Intraday stats                 │
                 └──────────────────────────────────┘

📦 2. COMPONENT FLOW DIAGRAM
App.tsx
  │
  ├── FutureHome.tsx  (Futures Routing Layer)
  │      │
  │      └── /futures/sessions  →  MarketSessions.tsx
  │              │
  │              ├─ imports CONTROL_MARKETS
  │              ├─ imports FUTURE_OPTIONS
  │              ├─ uses useMarketSessions()
  │              ▼
  │        MarketSessionCard.tsx
  │              │
  │              ├─ uses marketSessionUtils
  │              ├─ renders TOTAL or FUTURE layout
  │              └─ renders intraday + session stats
  │
  └── (other futures pages)


This clearly separates:

Routing

Session List Container

Card Component

Utilities

Hooks

Type definitions

🗺️ 3. DEPENDENCY MAP

This map shows who depends on whom.

MarketSessions.tsx
   ├── imports useMarketSessions.ts
   ├── imports CONTROL_MARKETS / FUTURE_OPTIONS
   └── imports → MarketSessionCard.tsx

MarketSessionCard.tsx
   ├── imports marketSessionUtils.ts
   ├── imports CONTROL_MARKETS (optional)
   └── receives props from MarketSessions.tsx

useMarketSessions.ts
   ├── fetches API data (backend)
   ├── returns grouped rows + live status
   ├── returns intraday snapshots
   └── returns selected future state

marketSessionUtils.ts
   ├── standalone helpers
   ├── formatting utilities
   ├── delta color logic
   └── date/session helpers

marketSessionTypes.ts
   ├── CONTROL_MARKETS list
   ├── FUTURE_OPTIONS list
   └── shared TS interfaces

Important relationships

MarketSessionCard must not call the API

MarketSessions must not contain calculation-heavy code

marketSessionUtils must not import React

useMarketSessions must not render UI

These boundaries prevent file explosion and keep everything modular.

🚀 4. FUTURE ROADMAP (Recommended Direction for the Module)

Here is a professional roadmap to evolve this into a best-in-class modular system.

Phase 1 — Split the Card Further (HIGH VALUE)

Create subcomponents inside /market/components/:

MarketHeader.tsx
MarketTopBar.tsx
MarketTotalCard.tsx
MarketFutureCard.tsx
MarketBBOPanel.tsx
MarketRangeMetrics.tsx
MarketMetaBlocks.tsx
MarketSessionStats.tsx
MarketIntradayPanel.tsx


These are all copy/paste extractions.

Goal:
Reduce any file above 200 lines.

Phase 2 — Move Inline Styles Into CSS Modules

Replace:

<style>{` ...huge block... `}</style>


With:

marketSessions.module.css
marketCard.module.css
marketStats.module.css


Benefits:

Faster renders

Smaller TSX files

No more giant inline CSS blocks

Phase 3 — Implement Virtualization (Performance Boost)

If we end up supporting:

15+ countries

100+ futures

multiple intraday panels

Then use:

react-window
or
react-virtualized


This keeps rendering O(1) instead of O(N).

Phase 4 — Add a Context Provider (Optional)

Move session selection and polling logic into:

MarketSessionProvider.tsx


So the UI becomes even more thin and focused.

Phase 5 — Unify Backend / Frontend Shape Definitions

Create shared types:

types/MarketSessionTypes.ts
types/IntradayTypes.ts


Then make backend return the same shape.

Zero guessing → zero bugs.

Phase 6 — Add Snapshot Debug Panel (Developer Tool)

A hidden debug panel (press D key) showing:

API timestamps

Last intraday update

Selected symbol

Worker timestamps

Delay calculations

This would immediately reveal when the backend produces slow updates.

🎯 Final Summary

Your Market Sessions system is now:

Modular

Splittable

Scalable

Performance-friendly

Easy to onboard new developers

Cleanly documented

The diagrams show flow, responsibilities, dependencies, and the future roadmap.