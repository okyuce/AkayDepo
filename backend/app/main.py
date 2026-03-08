from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

VERSION = "2.0.06"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: orphan verileri temizle (depot_id NULL olan kayıtlar)"""
    from app.core.database import engine
    from sqlmodel import Session, text

    try:
        with Session(engine) as session:
            # depot_id'si NULL olan istasyonları sil (eski sistemden kalma)
            result = session.exec(text("DELETE FROM stations WHERE depot_id IS NULL"))
            if result.rowcount > 0:
                logger.info(f"Startup: {result.rowcount} orphan istasyon silindi (depot_id NULL)")

            # depot_id'si NULL olan kullanıcıları temizle (superadmin ve dashboard hariç)
            result = session.exec(text(
                "DELETE FROM users WHERE depot_id IS NULL AND role NOT IN ('superadmin', 'admin')"
            ))
            if result.rowcount > 0:
                logger.info(f"Startup: {result.rowcount} orphan kullanıcı silindi (depot_id NULL)")

            session.commit()
    except Exception as e:
        logger.warning(f"Startup orphan temizleme hatası: {e}")

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
