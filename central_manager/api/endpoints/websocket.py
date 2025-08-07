import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

async def send_dashboard_updates(app):
    """Periodically fetches and sends dashboard updates to all connected clients."""
    while True:
        try:
            orchestrator = app.state.orchestrator
            summary_data = orchestrator.get_all_cameras_summary()

            # Processar os dados para o formato que o dashboard espera
            cameras_ativas = sum(1 for cam in summary_data if cam.get('running'))
            total_cameras = len(app.state.registered_cameras)

            dashboard_payload = {
                "type": "dashboard_update",
                "data": {
                    "status": "Online",
                    "cameras_ativas": cameras_ativas,
                    "total_cameras": total_cameras,
                    "alertas_pendentes": 0,  # Placeholder
                    "cameras": summary_data
                }
            }

            await manager.broadcast(json.dumps(dashboard_payload))
        except Exception as e:
            print(f"Error sending dashboard update: {e}")
        await asyncio.sleep(2) # Update interval

@router.websocket("/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    # Start the update task if it's the first connection
    if len(manager.active_connections) == 1:
        # We pass the app object to the task
        websocket.app.state.dashboard_update_task = asyncio.create_task(send_dashboard_updates(websocket.app))
    try:
        while True:
            # Keep the connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # If no clients are connected, cancel the update task
        if not manager.active_connections and hasattr(websocket.app.state, 'dashboard_update_task'):
            websocket.app.state.dashboard_update_task.cancel()
