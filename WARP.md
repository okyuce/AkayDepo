# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

**AkayDepo** is a warehouse transfer management system for PMI ISMS order data. It processes Excel imports, performs territory-based station planning, and provides a tablet interface for tracking loadsheet completion. The system operates on 3 daily cycles (14:00, 16:00, 17:00).

**Tech Stack:**
- Backend: FastAPI (Python 3.11), SQLModel ORM, PostgreSQL 14, Redis 7, Alembic migrations, WebSocket
- Frontend: React 18, TypeScript, Vite, Zustand (state), TailwindCSS, React Router
- Infrastructure: Docker Compose, Nginx (production proxy)

## Development Commands

### Essential Make Commands
```bash
make up           # Start all services in background
make down         # Stop all services
make dev          # Start in foreground with logs
make logs         # Follow all logs
make logs-api     # Follow backend logs only
make logs-web     # Follow frontend logs only
make migrate      # Run database migrations
make seed         # Load test data
make reset-db     # Reset database and reload seed data
make test         # Run backend tests
make clean        # Remove all containers and volumes
```

### Database Operations
```bash
# Create new migration (manual changes)
docker-compose exec api alembic revision --autogenerate -m "description"

# Apply migrations
make migrate

# Downgrade one migration
docker-compose exec api alembic downgrade -1

# Access PostgreSQL shell
docker-compose exec db psql -U depo -d akaydepo
```

### Testing
```bash
# Run all backend tests
make test

# Run specific test file
docker-compose exec api pytest tests/test_auth.py -v

# Run specific test function
docker-compose exec api pytest tests/test_auth.py::test_login -v

# Run with output
docker-compose exec api pytest -v -s
```

### Shell Access
```bash
# Backend container
make shell-api

# Frontend container
make shell-web

# Database container
docker-compose exec db bash
```

### Production Deployment
```bash
# Deploy to production
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Run migrations in production
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# View production logs
docker-compose -f docker-compose.prod.yml logs -f api
```

## Code Architecture

### Backend Structure (`backend/app/`)

**Core Services:**
- `services/cycle_manager.py` - Orchestrates cycle lifecycle, handles Excel import, revision detection, cycle completion
- `services/excel_parser.py` - Parses Excel files, validates data, creates territory/dealer/product/order entities
- `services/station_planner.py` - Greedy algorithm for distributing territories across stations, load balancing
- `services/loadsheet_generator.py` - Generates loadsheets from station assignments, handles package numbering (T07-B01 format)

**API Endpoints (`api/`):**
- `auth.py` - JWT authentication, login/logout, user management
- `cycles.py` - Excel import, cycle status, cancel pending orders
- `planning.py` - Create and retrieve station planning
- `loadsheets.py` - Tablet interface, loadsheet details, completion
- `counters.py` - Counter readings (vehicle odometer)
- `websocket.py` - Real-time updates for stations and cycles

**Models (`models/`):**
- Core entities: Cycle, Territory, Dealer, Product, Order, OrderLine
- Planning: Station, StationAssignment, Loadsheet, LoadsheetLine
- Tracking: LoadCounter, RevisionDiff

**Core (`core/`):**
- `config.py` - Settings management via pydantic-settings
- `database.py` - SQLModel engine and session management
- `websocket.py` - WebSocket connection manager

### Frontend Structure (`frontend/src/`)

**Pages:**
- Login page - JWT authentication
- Excel upload page - Cycle creation and station planning
- Tablet page - Station-specific loadsheet viewing and completion

**Key Patterns:**
- State management via Zustand stores (`stores/`)
- API calls abstracted in services (`services/`)
- Custom hooks for reusable logic (`hooks/`)
- Component composition (`components/`)

### Data Flow

**1. Cycle Creation (Excel Import):**
```
Excel → excel_parser.parse() → Validate → cycle_manager.create_cycle()
→ Create Territories, Dealers, Products, Orders
→ Return Cycle with status "active"
```

**2. Station Planning:**
```
cycle_manager.plan_cycle(cycle_id, num_stations)
→ station_planner.plan_stations(territories_with_loads, num_stations)
→ Greedy algorithm: Sort by load desc, assign to least loaded station
→ loadsheet_generator.generate_loadsheets(assignments)
→ Create Loadsheets with package numbers (Territory display + Dealer sequence)
```

**3. Tablet Workflow:**
```
Login → WebSocket connect to /ws/station/{station_id}
→ Fetch loadsheets via GET /v1/loadsheets/station/{station_id}
→ View loadsheet detail → Mark complete via POST /v1/loadsheets/{id}/complete
→ WebSocket broadcasts update → All connected clients refresh
```

**4. Revision System:**
```
Cycle N completes → Cycle N+1 imports
→ cycle_manager.detect_revisions(current_cycle, previous_cycle)
→ Diff at dealer-product level → Create revision loadsheets
→ parent_loadsheet_id references original, is_revision=true
```

### Key Business Rules

**Load Calculation:**
- 1 Karton = 10 Paket (conversion rule)
- Territory total load = sum(qty_carton + qty_pack/10) across all dealers

**Station Assignment Algorithm (Greedy):**
1. Sort territories by total load (descending)
2. Assign each territory to the station with lowest current load
3. Check imbalance: if max_load > avg_load × 1.5, add more stations
4. Target: balanced distribution across available stations

**Package Numbering:**
- Format: `T{territory_display_num}-B{dealer_sequence}`
- Example: T07-B01 (Territory 7, Dealer sequence 1)
- Dealers sorted by route_order within territory

**Revision Detection:**
- Compare current cycle vs previous cycle at dealer-product level
- Changes: qty_carton or qty_pack differ
- Creates new loadsheet with is_revision=true and parent reference

**Cycle States:**
- `active` - Current cycle accepting loads
- `completed` - All loadsheets processed
- `cancelled` - Cycle terminated

## Authentication

**JWT Token System:**
- Hardcoded users in `backend/app/api/auth.py` (USERS dict)
- Token expiry: 8 hours (default)
- Stored in localStorage on frontend
- Included in API requests as `Authorization: Bearer {token}`

**Test Users:**
- Admin: `admin` / `admin123` (full access)
- Tablets: `tablet1-5` / `tablet123` (station-specific)

## Access Points

- Frontend: http://localhost:8000
- Backend API: http://localhost:8001
- API Docs (Swagger): http://localhost:8001/docs
- Database: localhost:5432 (user: depo, password: depo123, db: akaydepo)
- Redis: localhost:6379

## Key Domain Concepts

**Cycle:** A time-bound batch of orders (14:00, 16:00, or 17:00). One active cycle at a time.

**Territory:** Geographical grouping of dealers (14 total: T01-T14). Each has a display number for labeling.

**Dealer:** Individual customer (53 total). Belongs to one territory, has route_order for sequencing.

**Station:** Loading station (5 default, configurable). Assigned territories via planning algorithm.

**Loadsheet:** Physical loading slip. One per dealer per cycle. Contains order lines for that dealer.

**Revision:** When a new cycle modifies an existing dealer's order. Creates a delta loadsheet.

**Counter:** Vehicle odometer reading at cycle start/end per station.

## WebSocket Channels

**`/ws/station/{station_id}`** - Tablet updates
- Message types: `loadsheet_completed`, `counter_reading`
- Broadcasts to all clients connected to same station

**`/ws/cycle`** - Admin dashboard (for monitoring all cycles)
- Message types: `cycle_completed`, `loadsheet_completed`

## Environment Configuration

**Backend (.env):**
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - JWT signing key
- `ENVIRONMENT` - development/production
- `CORS_ORIGINS` - Allowed frontend origins

**Frontend (.env):**
- `VITE_API_URL` - Backend API URL
- `VITE_WS_URL` - WebSocket URL

## Testing Notes

- Backend tests use in-memory SQLite (not PostgreSQL)
- Fixtures in `tests/conftest.py`: session, client, auth_token, auth_headers
- No frontend tests currently implemented (recommended: Jest + React Testing Library)

## Documentation

Detailed specs in `depo-transfer-docs/`:
- `CYCLE_MANAGEMENT.md` - Core cycle system (READ FIRST)
- `DATA_MODEL.md` - Database schema
- `BACKEND_API_SPEC.md` - Full API reference
- `UI_SPEC.md` - Frontend specifications
- `ALGO_STATIONS.md` - Station planning algorithm details
- `WORKLIST.md` - Development phases

## Important Notes

- **Port Configuration:** Frontend uses 8000, Backend uses 8001 (reversed from typical)
- **Hot Reload:** Both services support hot reload (FastAPI --reload, Vite HMR)
- **Migration Safety:** Always review auto-generated migrations before applying
- **WebSocket Auth:** No token verification on WebSocket connections (assumes trusted network)
- **Production Changes:** Update `USERS` dict to use database-backed authentication
- **SSL Setup:** See DEPLOYMENT.md for Let's Encrypt configuration
