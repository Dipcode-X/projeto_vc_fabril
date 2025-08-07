"""
Endpoints para dashboard e monitoramento
"""

from fastapi import APIRouter, Request

router = APIRouter(tags=["Dashboard"])

@router.get("/dashboard")
async def get_dashboard_overview(request: Request):
    """Retorna visão geral do sistema para o dashboard inicial."""
    orchestrator = request.app.state.orchestrator
    
    # Em uma aplicação real, estes dados viriam de um banco ou de uma camada de serviço
    # Por enquanto, vamos simular e pegar dados básicos do orquestrador
    
    all_cameras = orchestrator.get_all_cameras_summary()
    total_cameras = len(all_cameras)
    active_cameras = sum(1 for cam in all_cameras if cam.get('running'))

    return {
        "system_status": "Online" if total_cameras > 0 and active_cameras > 0 else "Parcialmente Online",
        "cameras_active": active_cameras,
        "cameras_total": total_cameras,
        "alerts_pending": 0, # Placeholder
    }
