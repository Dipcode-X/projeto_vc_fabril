"""
API endpoint for streaming visualized camera feeds.
"""

import asyncio
import cv2
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from queue import Empty  # Catch correct exception from standard Queue

from central_manager.database.connection import DatabaseManager

router = APIRouter(prefix="/streams", tags=["streams"])

# Helper to resolve processor from camera_id
def _resolve_processor(request: Request, camera_id: int):
    db = DatabaseManager()
    cam = db.get_camera(camera_id)
    if not cam:
        return None, None, None
    source = cam.device_index if cam.device_index is not None else cam.ip_address
    if source is None:
        return cam, None, None
    orchestrator = request.app.state.orchestrator
    processor = orchestrator.get_camera_data(source)
    return cam, source, processor

async def get_frame_from_processor(request: Request, camera_id: int):
    """
    Generator function to yield JPEG frames from a camera processor's queue.
    """
    db_manager = DatabaseManager()
    camera = db_manager.get_camera(camera_id)
    if not camera:
        return

    # Resolve camera source generically (USB index or IP/URL)
    camera_source = camera.device_index if camera.device_index is not None else camera.ip_address
    if camera_source is None:
        return

    orchestrator = request.app.state.orchestrator
    processor = orchestrator.get_camera_data(camera_source)

    if not processor:
        # This case is important if the camera is in the DB but not running.
        return

    # This queue is where CameraProcessor puts its visualized frames.
    frame_queue = processor.output_queue

    while True:
        try:
            # Stop if client disconnected to avoid busy work
            if await request.is_disconnected():
                break

            # Get a frame from the queue. This is a blocking call with timeout.
            data = await asyncio.to_thread(frame_queue.get, True, 5)
            frame = data.get('frame') if isinstance(data, dict) else None

            if frame is None:
                continue

            # Encode the frame as JPEG.
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue

            frame_bytes = buffer.tobytes()

            # Yield the frame in the multipart format.
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        except Empty:
            # If the queue is empty, wait a bit before trying again.
            await asyncio.sleep(0.05)
        except Exception:
            # If any other error occurs, stop the stream.
            break

@router.get("/camera/{camera_id}", summary="Get visualized video stream for a camera")
async def stream_camera_feed(request: Request, camera_id: int):
    """
    Provides a real-time MJPEG stream of the visualized feed for a specific camera.
    """
    db_manager = DatabaseManager()
    camera = db_manager.get_camera(camera_id)

    if not camera:
        raise HTTPException(status_code=404, detail=f"Câmera com ID {camera_id} não encontrada.")

    # Resolve source (supports USB index or IP/URL)
    camera_source = camera.device_index if camera.device_index is not None else camera.ip_address
    if camera_source is None:
        raise HTTPException(status_code=400, detail=f"Câmera com ID {camera_id} não possui fonte válida (device_index/ip).")

    orchestrator = request.app.state.orchestrator
    processor = orchestrator.get_camera_data(camera_source)

    if not processor or not processor.running:
        raise HTTPException(status_code=404, detail=f"Processador para a câmera {camera_id} não está em execução.")

    return StreamingResponse(
        get_frame_from_processor(request, camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

# --- Diagnostics ---
@router.get("/debug/{camera_id}")
async def debug_camera(request: Request, camera_id: int):
    cam, source, processor = _resolve_processor(request, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera não encontrada no banco")
    if source is None:
        raise HTTPException(status_code=400, detail="Camera sem fonte (device_index/ip)")
    running = bool(getattr(processor, 'running', False)) if processor else False
    qsize = int(processor.output_queue.qsize()) if processor else 0
    return {
        "camera_id": camera_id,
        "source": source,
        "processor_found": processor is not None,
        "running": running,
        "queue_size": qsize,
    }

@router.get("/snapshot/{camera_id}")
async def snapshot(request: Request, camera_id: int):
    cam, source, processor = _resolve_processor(request, camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail="Camera não encontrada no banco")
    if source is None:
        raise HTTPException(status_code=400, detail="Camera sem fonte (device_index/ip)")
    if not processor or not processor.running:
        raise HTTPException(status_code=404, detail="Processador não está rodando")

    # Tenta pegar um frame recente rapidamente
    try:
        data = await asyncio.to_thread(processor.output_queue.get, True, 2)
        frame = data.get('frame') if isinstance(data, dict) else None
        if frame is None:
            raise HTTPException(status_code=500, detail="Frame vazio")
        ok, buf = cv2.imencode('.jpg', frame)
        if not ok:
            raise HTTPException(status_code=500, detail="Falha ao codificar JPEG")
        return StreamingResponse(iter([buf.tobytes()]), media_type='image/jpeg')
    except Empty:
        raise HTTPException(status_code=504, detail="Sem frames disponíveis (fila vazia)")
