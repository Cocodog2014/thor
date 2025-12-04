
// marketSessionStyles.ts
export const MARKET_SESSIONS_STYLES = `
  .market-dashboard { width: 100%; padding: 16px; }
  .market-dashboard-header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 10px; }
  .market-open-header-title { font-size: 1.05rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
  .subtitle-text { opacity: 0.75; }

  .market-grid { display: grid; grid-template-columns: 1fr; gap: 14px; }
  .mo-rt-card { background: #1e1e1e; border-radius: 12px; /* ...rest of that line from your TSX */ }
  .mo-rt-left { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 10px; }
  .mo-rt-right { flex: 0 0 auto; min-width: 280px; }

  .mo-rt-header { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
  .mo-rt-header-chips { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
  .chip { padding: 3px 8px; border-radius: 999px; /* ... */ }
  .chip.sym { background: rgba(255,255,255,0.15); }
  .chip.weight { background: rgba(0,0,0,0.4); }
  .chip.default { background: rgba(148,163,184,0.35); }
  .chip.signal.success { background: rgba(16,185,129,0.35); }
  .chip.signal.error { background: rgba(239,68,68,0.35); }
  .chip.signal.warning { background: rgba(255,193,7,0.35); }
  .chip.status.success { background: rgba(16,185,129,0.35); }
  .chip.status.error { background: rgba(239,68,68,0.35); }
  .chip.status.warning { background: rgba(255,193,7,0.35); }

  /* keep copying everything that was between <style>{ and }</style> */

  .session-stats-header span:first-child,
  .session-stats-row span:first-child { text-align: left; }
  .session-stats-row + .session-stats-row { /* ... */ }
  .triangle-cell { display:flex; align-items:center; justify-content:center; }
  .triangle-percent { font-size: 11px; font-weight: 600; }
  .triangle-up { /* ... */ }
  .triangle-down { /* ... */ }
  .triangle-neutral { /* ... */ }

  @media (max-width: 900px) {
    .mo-rt-right { min-width: 0; }
    .mo-rt-right-columns { grid-template-columns: 1fr; }
  }
`;


