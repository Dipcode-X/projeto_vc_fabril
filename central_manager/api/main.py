"""
Main entry point for the SIAC FastAPI application.

This application serves the SIAC system's data and video streams
to a web-based dashboard.
"""

import uvicorn
from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from central_manager.core_advanced.orchestrator import Orchestrator
from central_manager.api.endpoints import dashboard, cameras, setores, produtos, websocket

# --- API Router Setup ---
api_router = APIRouter()
api_router.include_router(dashboard.router)
api_router.include_router(cameras.router)
api_router.include_router(setores.router)
api_router.include_router(produtos.router)
api_router.include_router(websocket.router)

# --- Application Setup ---
def create_app():
    """Creates and configures the FastAPI application and its resources."""
    # --- Mock Data / Config ---
    # No futuro, isso virá de um banco de dados
    REGISTERED_CAMERAS = [0, 1, 2] # Câmeras homologadas no sistema

    # --- Lifespan Events (Recommended Way) ---
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application startup and shutdown logic."""
        print("--- Application Startup ---")
        # Store shared state
        app.state.registered_cameras = REGISTERED_CAMERAS

        # Initialize and start the orchestrator
        orchestrator = Orchestrator()
        app.state.orchestrator = orchestrator
        
        # Adiciona todas as câmeras registradas ao orquestrador
        for cam_id in REGISTERED_CAMERAS:
            orchestrator.add_camera(cam_id)
        
        orchestrator.start()
        print("Orchestrator started.")
        
        yield
        
        print("--- Application Shutdown ---")
        app.state.orchestrator.stop()
        print("Orchestrator stopped.")

    app = FastAPI(
        title="SIAC Industrial - API",
        description="API para gerenciar o sistema SIAC.",
        lifespan=lifespan
    )

    # --- API Routers ---
    app.include_router(api_router, prefix="/api/v1")

    # --- Static Files (must be last) ---
    # Mount the static directory to serve the frontend
    app.mount("/", StaticFiles(directory="central_manager/static", html=True), name="static")

    return app

app = create_app()

# --- Health Check Endpoint ---
@app.get("/api/v1/status")
async def get_status():
    """Returns the current status of the API."""
    return {"status": "ok", "message": "SIAC API is running."}


if __name__ == "__main__":
    uvicorn.run(
        "central_manager.api.main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True, 
        reload_dirs=["central_manager"]
    )
