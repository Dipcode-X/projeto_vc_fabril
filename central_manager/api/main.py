"""
Main entry point for the SIAC FastAPI application.

This application serves the SIAC system's data and video streams
to a web-based dashboard.
"""

import uvicorn
import os
from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from fastapi.responses import FileResponse

from central_manager.core_advanced.orchestrator import Orchestrator
from central_manager.core_advanced.alert_manager import AlertManager
from central_manager.core_advanced.config import MQTT_CONFIG
from central_manager.api.endpoints import dashboard, cameras, setores, produtos, websocket

# --- API Router Setup ---
api_router = APIRouter()
api_router.include_router(dashboard.router)
api_router.include_router(cameras.router)
api_router.include_router(setores.router)
api_router.include_router(produtos.router)
# api_router.include_router(linhas.router)  # removed: module not found
api_router.include_router(websocket.router)
# api_router.include_router(streams.router)  # removed: module not found

# Health check via API router (registered before StaticFiles mount)
@api_router.get("/status")
async def api_status():
    return {"status": "ok", "message": "SIAC API is running."}

# --- Application Setup ---
def create_app():
    """Creates and configures the FastAPI application and its resources."""

    # --- Lifespan Events (Recommended Way) ---
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application startup and shutdown logic."""
        print("--- Application Startup ---")
        logger = logging.getLogger("FastAPI-Lifespan")
        logger.setLevel(logging.INFO)
        logger.info("--- INICIANDO APLICAÇÃO --- ")

        try:
            # Initialize a single AlertManager for the entire application.
            logger.info("Inicializando AlertManager...")
            alert_manager = AlertManager(
                broker_ip=MQTT_CONFIG['broker_ip'],
                broker_port=MQTT_CONFIG['broker_port'],
                client_id=MQTT_CONFIG['client_id']
            )
            app.state.alert_manager = alert_manager
            logger.info("AlertManager inicializado.")

            # Initialize and start the orchestrator.
            logger.info("Inicializando Orchestrator...")
            orchestrator = Orchestrator()
            app.state.orchestrator = orchestrator
            logger.info("Orchestrator inicializado, configurando modo de inicialização...")
            # Controla auto-start via variável de ambiente (0/1). Padrão: 1 (auto-start ativo).
            auto_start = os.getenv("SIAC_AUTO_START", "1")
            if auto_start in ("1", "true", "True"):
                logger.info("AUTO-START ATIVO: iniciando processamento das câmeras no startup...")
                orchestrator.start()
                logger.info("Orchestrator.start() chamado no startup.")
            else:
                logger.info("AUTO-START DESATIVADO: as câmeras serão iniciadas somente pelos endpoints /cameras/{id}/start.")
            
        except Exception as e:
            logger.error(f"Falha crítica durante o startup da aplicação: {e}", exc_info=True)
            # Opcional: decidir se a aplicação deve parar se o startup falhar.
            # Por exemplo, pode-se usar um sys.exit(1) ou deixar que o uvicorn handle.
            raise

        yield
        
        print("--- Application Shutdown ---")
        app.state.orchestrator.stop()
        print("Orchestrator stopped.")

    app = FastAPI(
        title="SIAC Industrial - API",
        description="API para gerenciar o sistema SIAC.",
        lifespan=lifespan
    )

    # Ensure default registered cameras list exists
    app.state.registered_cameras = []

    # --- API Routers ---
    app.include_router(api_router, prefix="/api/v1")

    # Resolve absolute paths for static directories
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    static_dir = os.path.join(base_dir, "static")
    react_dir = os.path.join(static_dir, "react")

    # Serve React index on '/app' (no trailing slash) to avoid 404
    @app.get("/app", include_in_schema=False)
    async def serve_react_index():
        react_index_path = os.path.join(react_dir, "index.html")
        return FileResponse(react_index_path)

    # --- Static Files (must be last) ---
    # Mount the React build at /app (separate from legacy static UI)
    app.mount("/app", StaticFiles(directory=react_dir, html=True), name="react")
    # Mount the static directory to serve the frontend
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

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
