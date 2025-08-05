"""
Endpoints para gerenciamento de câmeras
"""

from fastapi import APIRouter

router = APIRouter(prefix="/cameras", tags=["cameras"])

@router.get("/")
async def list_cameras():
    """Lista todas as câmeras disponíveis"""
    # TODO: Implementar
    pass

@router.post("/{camera_id}/start")
async def start_camera(camera_id: str, product_id: str):
    """Inicia processamento de uma câmera com produto específico"""
    # TODO: Implementar
    pass

@router.post("/{camera_id}/stop")
async def stop_camera(camera_id: str):
    """Para processamento de uma câmera"""
    # TODO: Implementar
    pass

@router.get("/{camera_id}/status")
async def get_camera_status(camera_id: str):
    """Retorna status atual de uma câmera"""
    # TODO: Implementar
    pass

@router.post("/{camera_id}/switch-product")
async def switch_camera_product(camera_id: str, product_id: str):
    """Troca produto de uma câmera em runtime"""
    # TODO: Implementar
    pass
