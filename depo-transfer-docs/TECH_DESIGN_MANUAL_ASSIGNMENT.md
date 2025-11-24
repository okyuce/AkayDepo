# Manual Territory→Station Assignment
Problem: Territory loads change over time, so the initial greedy balance drifts after new imports. Admins need a persistent, manual mapping of territory→station that planning can honor, with a switch to enable/disable automatic planning.
## Scope
- New drag–drop UI to assign all active territories to stations.
- Persistent mapping independent of cycles; planning uses it when auto-planning is disabled.
- Validation: Save is blocked if any territory remains unassigned. Reset clears all assignments.
- Stations can be toggled active/inactive; inactive stations are excluded from planning and their territories fall back to the pool.
- Navbar: Definitions → Territory Definitions, Territory Assignment.
## Data Model
- StationTerritoryMap (station_territory_map)
  - id (uuid, pk)
  - station_id (fk stations.id)
  - territory_code (str, unique) — master code from TerritoryInfo; ensures a territory maps to at most one station.
  - created_at (timestamp)
- PlanningConfig (planning_config)
  - id (uuid, pk; single row)
  - auto_planning_enabled (bool, default true)
  - updated_at (timestamp)
Notes: codes are stable (TerritoryInfo.update does not allow changing code), so mapping by code is safe.
## Backend API
- GET /v1/assignments/config
  - Returns: { auto_planning_enabled, stations: [{id,name,active}], assignments: [{station_id, territory_code}] }
- POST /v1/assignments/config
  - Body: { auto_planning_enabled: bool, assignments: [{station_id, territory_code}] }
  - Validates: all active territories (from TerritoryInfo where is_active) must appear exactly once; returns 400 if any missing or duplicates. Saves idempotently (replace-all semantics).
- POST /v1/assignments/reset
  - Clears mapping; territories return to pool.
- Optional: GET/PUT /v1/stations for active toggle (or reuse existing if present).
## Planning Integration
- In POST /v1/cycles/{cycle_id}/plan:
  - If PlanningConfig.auto_planning_enabled is true: current greedy flow.
  - Else: build StationAssignment by reading StationTerritoryMap for active stations only. Wipes existing StationAssignment for the cycle and inserts assignments in display order; then loadsheets are generated (existing generator).
## Frontend
- New page: TerritoryAssignmentPage
  - Top pool lists all active territories; assigned ones appear disabled and colored.
  - Below: N station columns with colored headers (stable palette; color computed deterministically by station id → palette index).
  - Drag–drop (HTML5 events) between pool and station columns; delete from station returns to pool.
  - Controls: Auto Planning [On/Off]; Save (disabled if any unassigned); Reset (moves all to pool); Station active toggles.
- Navbar: Definitions menu with links to Territory Definitions and Territory Assignment.
## Validation Rules
- No save if any active territory is unassigned.
- A territory can’t be assigned to multiple stations; enforced on UI and backend (unique on territory_code).
- Switching a station to inactive immediately returns its territories to pool; save required to persist.
## Deployment & Migration
- Alembic migration: create tables planning_config and station_territory_map.
- Backward compatible: if config row missing, default auto_planning_enabled=true.
## Testing
- API tests for: save mapping, reject missing territory, reset, plan respects manual mapping.
- UI smoke: DnD interactions, disabled Save with unassigned, coloring, toggles.
