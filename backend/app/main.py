from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

VERSION = "1.0.14"

app = FastAPI(
    title="AkayDepo API",
    description="Depo Transfer Yönetim Sistemi",
    version=VERSION
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
from app.api import cycles, planning, loadsheets, counters, websocket, auth, stations, territory_info, assignments, inventory, product_order, users

app.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
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
app.include_router(websocket.router, prefix="/ws", tags=["websocket"])
