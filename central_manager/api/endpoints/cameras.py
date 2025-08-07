"""
Endpoints para gerenciamento de câmeras
"""

import asyncio
import cv2
from fastapi import APIRouter, Request, HTTPException, Response
from starlette.responses import StreamingResponse

router = APIRouter(prefix="/cameras", tags=["cameras"])

@router.get("", summary="Lista todas as câmeras disponíveis")
async def get_cameras(request: Request):
    """Lists all available cameras and their current status."""
    orchestrator = request.app.state.orchestrator
    registered_cameras = request.app.state.registered_cameras
    active_cameras_summary = orchestrator.get_all_cameras_summary()

    # Cria um dicionário para acesso rápido aos status das câmeras ativas
    active_cameras_dict = {cam['id']: cam for cam in active_cameras_summary}

    cameras_list = []
    for camera_id in registered_cameras:
        camera_status = active_cameras_dict.get(camera_id)

        if camera_status:
            # A câmera está registrada e ativa
            status_message = camera_status.get('status_message', {})
            contagem_caixas = 0
            if isinstance(status_message, dict):
                contagem_caixas = status_message.get('total_caixas_finalizadas', 0)

            cameras_list.append({
                "id": camera_id,
                "nome": f"Câmera {camera_id}",
                "status": "active",
                "setor": "Produção A",  # Placeholder
                "produto_atual": camera_status.get('product_name', 'N/A'),
                "contagem_caixas": contagem_caixas
            })
        else:
            # A câmera está registrada, mas inativa
            cameras_list.append({
                "id": camera_id,
                "nome": f"Câmera {camera_id}",
                "status": "inactive",
                "setor": "Produção A",
                "produto_atual": "N/A",
                "contagem_caixas": 0
            })

    return cameras_list

@router.get("/{camera_id}/status", summary="Obtém o status detalhado de uma câmera")
async def get_camera_status(camera_id: int, request: Request):
    """Retorna o status em tempo real de uma câmera específica."""
    orchestrator = request.app.state.orchestrator
    camera_processor = orchestrator.processors.get(camera_id, {}).get('processor')

    if not camera_processor:
        raise HTTPException(status_code=404, detail=f"Câmera {camera_id} não encontrada ou não está ativa.")

    return camera_processor.get_status()

@router.post("/{camera_id}/start")
async def start_camera(camera_id: int, request: Request):
    """Starts a camera processor."""
    orchestrator = request.app.state.orchestrator
    orchestrator.start_processor(camera_id)
    return {"message": f"Camera {camera_id} started."}

@router.post("/{camera_id}/stop")
async def stop_camera(camera_id: int, request: Request):
    """Stops a camera processor."""
    orchestrator = request.app.state.orchestrator
    orchestrator.stop_processor(camera_id)
    return {"message": f"Camera {camera_id} stopped."}

async def frame_generator(camera_id: int, orchestrator):
    """Yields frames from a camera's output queue for streaming."""
    camera_data = orchestrator.get_camera_data(camera_id)
    if not camera_data:
        print(f"Error: No data for camera {camera_id} for streaming.")
        return

    output_queue = camera_data.get('queue')
    while True:
        try:
            data = await asyncio.to_thread(output_queue.get, timeout=1.0)
            frame = data['frame']
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except Exception:
            # If queue is empty or another error, keep trying
            await asyncio.sleep(0.1)

@router.get("/{camera_id}/stream")
async def camera_stream(camera_id: int, request: Request):
    """Provides an MJPEG stream for a camera."""
    orchestrator = request.app.state.orchestrator
    return StreamingResponse(
        frame_generator(camera_id, orchestrator),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )
