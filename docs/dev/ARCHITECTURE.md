# Thor Architecture

High-level system map and flows. See service-specific docs for details.

- Backend: Django (`thor-backend`)
- Frontend: React + Vite (`thor-frontend`)
- Storage: PostgreSQL, Parquet + DuckDB
- Cache/Bus: Redis (latest hashes + unified stream)
- Edge: Cloudflare Tunnel (dev)

Sections:
- System Diagram
- Data Flow: Excel/Schwab → Redis → API → UI
- Background Stack: supervisors and guards
- Deployment notes
