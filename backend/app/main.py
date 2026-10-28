from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path
import logging

from app.core.config import settings
from app.core.database import engine, Base, AsyncSessionLocal
from app.services.seed_data import seed_database
from app.services.ws_hub import ws_hub

# API Routers
from app.api.routes_facilities import router as facilities_router
from app.api.routes_docks import router as docks_router
from app.api.routes_appointments import router as appointments_router
from app.api.routes_gate import router as gate_router
from app.api.routes_doculog import router as doculog_router
from app.api.routes_edge import router as edge_router
from app.api.routes_simulation import router as simulation_router
from app.services.yard_simulator import yard_simulator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dockpulse")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables and seed default data
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Checking facility configuration...")
    async with AsyncSessionLocal() as session:
        await seed_database(session)
    
    logger.info("DockPulse backend initialized successfully.")
    yield
    # Shutdown
    logger.info("Shutting down DockPulse backend...")
    yard_simulator.stop()
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Depo Saha ve Rampa Yönetim Sistemi (Dock & Yard Management - YMS)",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket Realtime Hub
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_hub.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_hub.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket connection error: {e}")
        ws_hub.disconnect(websocket)

# Include Routers (API prefix /api/v1)
app.include_router(facilities_router, prefix=settings.API_V1_PREFIX)
app.include_router(docks_router, prefix=settings.API_V1_PREFIX)
app.include_router(appointments_router, prefix=settings.API_V1_PREFIX)
app.include_router(gate_router, prefix=settings.API_V1_PREFIX)
app.include_router(doculog_router, prefix=settings.API_V1_PREFIX)
app.include_router(edge_router, prefix=settings.API_V1_PREFIX)
app.include_router(simulation_router, prefix=settings.API_V1_PREFIX)

# Static Uploads Mount
uploads_dir = Path(__file__).resolve().parent.parent.parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Static Frontend Mount
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    logger.info(f"Mounting frontend dist from: {frontend_dist}")
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    @app.get("/")
    async def root():
        return {
            "project": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "status": "online",
            "docs": "/docs",
            "doculog_connected": settings.DOCULOG_SYNC_ENABLED
        }
