from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

VERSION = "2.0.45"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: tabloları oluştur ve orphan verileri temizle"""
    from app.core.database import engine, create_db_and_tables
    from sqlmodel import Session, text

    # Yeni tabloları oluştur (mevcut tablolara dokunmaz)
    create_db_and_tables()

    try:
        with Session(engine) as session:
            # Aktif döngüsü olan depoyu bul (orphan verileri bu depoya ata)
            row = session.execute(text(
                "SELECT DISTINCT depot_id FROM cycles WHERE depot_id IS NOT NULL LIMIT 1"
            )).first()

            if row:
                target_depot_id = row[0]
                # depot_id NULL olan tüm tabloları güncelle
                tables = [
                    "stations", "station_assignments", "station_territory_map",
                    "station_inventory", "stock_movements", "orders",
                    "territories", "territory_info", "loadsheets",
                    "dealers", "load_counters", "revision_diffs", "planning_config",
                    "cycle_imports", "cycles",
                ]
                for table in tables:
                    result = session.execute(text(
                        f"UPDATE {table} SET depot_id = :depot_id WHERE depot_id IS NULL"
                    ), {"depot_id": str(target_depot_id)})
                    if result.rowcount > 0:
                        logger.info(f"Startup: {table} tablosunda {result.rowcount} kayıt depot_id atandı")

                # Kullanıcılar — superadmin ve admin hariç
                result = session.execute(text(
                    "UPDATE users SET depot_id = :depot_id WHERE depot_id IS NULL AND role NOT IN ('superadmin', 'admin')"
                ), {"depot_id": str(target_depot_id)})
                if result.rowcount > 0:
                    logger.info(f"Startup: users tablosunda {result.rowcount} kayıt depot_id atandı")

                session.commit()
    except Exception as e:
        logger.warning(f"Startup orphan düzeltme hatası: {e}")

    yield


app = FastAPI(
    title="AkayDepo API",
    description="Depo Transfer Yönetim Sistemi",
    version=VERSION,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "AkayDepo API",
        "version": VERSION,
        "environment": settings.ENVIRONMENT
    }

@app.get("/v1/version")
async def get_version():
    return {"version": VERSION}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# API routers
from app.api import cycles, planning, loadsheets, counters, websocket, auth, stations, territory_info, assignments, inventory, product_order, users, dashboard, depots, superadmin

app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/v1/dashboard", tags=["dashboard"])
app.include_router(users.router, prefix="/v1/users", tags=["users"])
app.include_router(cycles.router, prefix="/v1/cycles", tags=["cycles"])
app.include_router(planning.router, prefix="/v1/cycles", tags=["planning"])
app.include_router(loadsheets.router, prefix="/v1/loadsheets", tags=["loadsheets"])
app.include_router(counters.router, prefix="/v1/counters", tags=["counters"])
app.include_router(stations.router, prefix="/v1/stations", tags=["stations"])
app.include_router(territory_info.router, prefix="/v1/territory-info", tags=["territory_info"])
app.include_router(assignments.router, prefix="/v1/assignments", tags=["assignments"])
app.include_router(inventory.router, prefix="/v1/inventory", tags=["inventory"])
app.include_router(product_order.router, prefix="/v1/product-order", tags=["product_order"])
app.include_router(depots.router, prefix="/v1/depots", tags=["depots"])
app.include_router(superadmin.router, prefix="/v1/superadmin", tags=["superadmin"])
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
