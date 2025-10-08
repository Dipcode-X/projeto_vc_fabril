"""
Endpoints para gerenciamento de câmeras
"""

import asyncio
import cv2
import json
import os
import re
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException, Response
from starlette.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter(prefix="/cameras", tags=["cameras"])

class ProdutoUpdate(BaseModel):
    produto_id: int

class ThresholdsUpdate(BaseModel):
    confianca_roi: float | None = None
    confianca_item: float | None = None
    confianca_divisor: float | None = None
    # Chaves avançadas do StateManager (runtime)
    percentual_itens_novos_salto: float | None = None
    percentual_itens_novos_minimo: float | None = None
    usar_validacao_divisor_salto: bool | None = None
    # Tempos/inteiros (segundos, não normalizados 0..1)
    tempo_divisor_estavel_minimo: float | None = None
    tempo_maximo_instabilidade_divisor: float | None = None

class CameraIdentificacaoUpdate(BaseModel):
    ip_address: str | None = None
    bancada: str | None = None

@router.get("", summary="Lista todas as câmeras disponíveis")
async def get_cameras(request: Request):
    """Lists all available cameras and their current status."""
    orchestrator = request.app.state.orchestrator
    registered_cameras = orchestrator.get_registered_cameras()
    active_cameras_summary = orchestrator.get_all_cameras_summary()

    # Cria um dicionário para acesso rápido aos status das câmeras ativas
    active_cameras_dict = {cam['id']: cam for cam in active_cameras_summary}

    # Buscar dados das câmeras no banco de dados
    from central_manager.database.connection import DatabaseManager
    db_manager = DatabaseManager()
    cameras_list = []
    db_cameras = db_manager.get_all_cameras(ativo_only=False)
    
    # Adiciona câmeras do banco de dados que podem não estar no orquestrador
    for db_camera in db_cameras:
        # Verifica se a câmera já foi adicionada (para evitar duplicatas)
        if not any(c['id'] == db_camera.id for c in cameras_list):
            linha = db_manager.get_linha(db_camera.linha_id)
            setor = db_manager.get_setor(linha.setor_id) if linha else None
            produto = db_manager.get_produto(db_camera.produto_id)
            
            cameras_list.append({
                "id": db_camera.id,
                "nome": db_camera.nome,
                "bancada": getattr(db_camera, 'bancada', None),
                "ip_address": getattr(db_camera, 'ip_address', None),
                "device_index": getattr(db_camera, 'device_index', None),
                "porta": getattr(db_camera, 'porta', None),
                # O status será 'inactive' por padrão e atualizado se estiver no orquestrador
                "status": "inactive", 
                "setor": setor.nome if setor else "Setor Desconhecido",
                "setor_id": setor.id if setor else None,
                "linha_id": linha.id if linha else None,
                "linha_nome": linha.nome if linha else "Linha Desconhecida",
                "produto_atual": produto.nome if produto else "N/A",
                "produto_id": produto.id if produto else None,
                "contagem_caixas": 0
            })

    # Atualiza com dados do orquestrador (câmeras ativas)
    for cam_data in active_cameras_summary:
        # Tenta encontrar a câmera do DB correspondente pela fonte (ip ou device_index)
        source = cam_data.get('id')
        db_cam = next((c for c in db_cameras if str(c.device_index) == str(source) or c.ip_address == str(source)), None)
        
        if db_cam:
            # Encontra a entrada na lista e atualiza seu status para 'active'
            entry = next((c for c in cameras_list if c['id'] == db_cam.id), None)
            if entry:
                entry['status'] = 'active'
                status_message = cam_data.get('status_message', {})
                contagem_caixas = 0
                if isinstance(status_message, dict):
                    contagem_caixas = status_message.get('total_caixas_finalizadas', 0)
                entry['contagem_caixas'] = contagem_caixas
        else:
            # Se a câmera ativa não está no banco, loga um aviso mas não a adiciona à lista
            # para evitar dados inconsistentes na UI.
            print(f"AVISO: Câmera ativa com source '{source}' não encontrada no banco de dados.")

    return cameras_list

# ---- Criação de câmera (Option A: setor_id + bancada; ou linha_id explícito) ----
class CameraCreatePayload(BaseModel):
    # Vínculo
    linha_id: Optional[int] = None
    setor_id: Optional[int] = None
    bancada: Optional[str] = None  # A/B
    nome: Optional[str] = None
    produto_id: int

    # Conectividade
    device_index: Optional[int] = None
    ip_address: Optional[str] = None
    porta: Optional[int] = None

    # Vídeo
    resolucao_width: Optional[int] = 1920
    resolucao_height: Optional[int] = 1080
    fps: Optional[int] = 30

    # Extras
    config_json: Optional[Dict[str, Any]] = None
    ativo: Optional[bool] = True

@router.post("", summary="Cria uma nova câmera")
async def create_camera(payload: CameraCreatePayload, request: Request):
    from central_manager.database.connection import DatabaseManager
    from central_manager.models import database_models
    db = DatabaseManager()

    # Produto deve existir
    if not db.get_produto(payload.produto_id):
        raise HTTPException(status_code=404, detail=f"Produto {payload.produto_id} não encontrado")

    # Bancada (quando enviada)
    banca = None
    if payload.bancada is not None:
        b = str(payload.bancada).strip().upper()
        if b not in ("A", "B"):
            raise HTTPException(status_code=400, detail="bancada deve ser 'A' ou 'B'")
        banca = b

    # Fonte: exatamente um entre device_index e ip_address
    if ((payload.device_index is None and not payload.ip_address) or
        (payload.device_index is not None and payload.ip_address)):
        raise HTTPException(status_code=400, detail="Informe apenas um: device_index OU ip_address")

    # Validação IP + unicidade
    ip = None
    if payload.ip_address:
        ip = str(payload.ip_address).strip()
        is_url = ip.startswith("rtsp://") or ip.startswith("http://") or ip.startswith("https://")
        is_ipv4 = bool(re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", ip))
        if not (is_url or is_ipv4):
            raise HTTPException(status_code=400, detail="ip_address deve ser IPv4 ou URL RTSP/HTTP")
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM cameras WHERE ip_address = ?", (ip,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="ip_address já está em uso por outra câmera")

    # device_index único quando definido
    if payload.device_index is not None:
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM cameras WHERE device_index = ?", (payload.device_index,))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="device_index já cadastrado em outra câmera")

    # Resolver linha
    linha_id = payload.linha_id
    if linha_id is None:
        if payload.setor_id is None:
            raise HTTPException(status_code=400, detail="linha_id ou setor_id devem ser informados")
        line_name = f"Linha Bancada {banca}" if banca else "Linha (auto)"
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM linhas WHERE setor_id = ? AND nome = ?", (payload.setor_id, line_name))
            row = cur.fetchone()
            if row:
                linha_id = int(row[0] if isinstance(row, tuple) else row['id'])
            else:
                linha_obj = database_models.LinhaCreate(setor_id=payload.setor_id, nome=line_name, descricao=None, ativo=True)
                created_linha = db.create_linha(linha_obj)
                linha_id = created_linha.id

    # Enforce 1 câmera por linha
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM cameras WHERE linha_id = ?", (linha_id,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="Já existe uma câmera cadastrada para esta linha")

    # Nome default
    nome = payload.nome or (f"Bancada {banca}" if banca else "Camera")

    # Criar via DatabaseManager (usa defaults do DB para vídeo quando None)
    cam_create = database_models.CameraCreate(
        linha_id=linha_id,
        produto_id=payload.produto_id,
        nome=nome,
        device_index=payload.device_index,
        ip_address=ip,
        porta=payload.porta,
        bancada=banca,
        resolucao_width=payload.resolucao_width,
        resolucao_height=payload.resolucao_height,
        fps=payload.fps,
        usuario=None,
        senha=None,
        config_json=payload.config_json or {},
        ativo=True if payload.ativo is None else bool(payload.ativo),
    )
    created = db.create_camera(cam_create)

    return {
        "message": "Câmera criada com sucesso",
        "camera": created.model_dump() if hasattr(created, 'model_dump') else created.dict(),
    }

class CameraUpdatePayload(BaseModel):
    # Identificação e vínculo
    nome: Optional[str] = None
    bancada: Optional[str] = None
    setor_id: Optional[int] = None
    linha_id: Optional[int] = None

    # Conectividade
    device_index: Optional[int] = None
    ip_address: Optional[str] = None  # "" ou null para limpar
    porta: Optional[int] = None

    # Vídeo
    resolucao_width: Optional[int] = None
    resolucao_height: Optional[int] = None
    fps: Optional[int] = None

    # Outros
    ativo: Optional[bool] = None
    config_json: Optional[Dict[str, Any]] = None

@router.put("/{camera_id}", summary="Atualiza dados gerais da câmera")
async def update_camera(camera_id: int, body: CameraUpdatePayload, request: Request):
    from central_manager.database.connection import DatabaseManager
    from central_manager.models import database_models
    db = DatabaseManager()

    cam = db.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Câmera {camera_id} não encontrada")

    # Preparar valores finais (default = atuais)
    final_nome = cam.nome
    final_bancada = getattr(cam, 'bancada', None)
    final_setor_id = None  # só usado para mover de linha
    final_linha_id = cam.linha_id
    final_device_index = cam.device_index
    final_ip = cam.ip_address
    final_porta = cam.porta
    final_rw = cam.resolucao_width
    final_rh = cam.resolucao_height
    final_fps = cam.fps
    final_ativo = cam.ativo
    final_cfg = cam.config_json if getattr(cam, 'config_json', None) is not None else {}

    # Nome
    if body.nome is not None:
        final_nome = str(body.nome).strip() or final_nome

    # Bancada
    if body.bancada is not None:
        b = str(body.bancada).strip().upper()
        if b not in ("A", "B"):
            raise HTTPException(status_code=400, detail="bancada deve ser 'A' ou 'B'")
        final_bancada = b

    # Linha/Setor (Option A: setor_id + bancada define/resolve linha)
    if body.linha_id is not None:
        final_linha_id = int(body.linha_id)
    elif body.setor_id is not None:
        final_setor_id = int(body.setor_id)
        line_name = f"Linha Bancada {final_bancada}" if final_bancada else "Linha (auto)"
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM linhas WHERE setor_id = ? AND nome = ?", (final_setor_id, line_name))
            row = cur.fetchone()
            if row:
                final_linha_id = int(row[0] if isinstance(row, tuple) else row['id'])
            else:
                linha_obj = database_models.LinhaCreate(setor_id=final_setor_id, nome=line_name, descricao=None, ativo=True)
                nova = db.create_linha(linha_obj)
                final_linha_id = nova.id

    # Conectividade: ip/device
    device_in_payload = (body.device_index is not None)
    ip_in_payload = (body.ip_address is not None)

    if device_in_payload and ip_in_payload:
        raise HTTPException(status_code=400, detail="Informe apenas um: device_index OU ip_address")

    if device_in_payload:
        final_device_index = body.device_index

    if ip_in_payload:
        ip = body.ip_address
        if ip is None or str(ip).strip() == "":
            final_ip = None
        else:
            ip = str(ip).strip()
            is_url = ip.startswith("rtsp://") or ip.startswith("http://") or ip.startswith("https://")
            is_ipv4 = bool(re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", ip))
            if not (is_url or is_ipv4):
                raise HTTPException(status_code=400, detail="ip_address deve ser IPv4 ou URL RTSP/HTTP")
            final_ip = ip

    # CHECK: deve permanecer com exatamente uma fonte (apenas quando fonte for alterada neste payload)
    if (device_in_payload or ip_in_payload):
        if ((final_device_index is None and (final_ip is None or final_ip == "")) or
            (final_device_index is not None and final_ip not in (None, ""))):
            raise HTTPException(status_code=400, detail="A câmera deve ter apenas uma fonte: device_index OU ip_address")

    # Unicidades quando alterados
    with db.get_connection() as conn:
        cur = conn.cursor()
        if final_ip not in (None, "") and final_ip != cam.ip_address:
            cur.execute("SELECT id FROM cameras WHERE ip_address = ? AND id <> ?", (final_ip, camera_id))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="ip_address já está em uso por outra câmera")
        if final_device_index is not None and final_device_index != cam.device_index:
            cur.execute("SELECT id FROM cameras WHERE device_index = ? AND id <> ?", (final_device_index, camera_id))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="device_index já cadastrado em outra câmera")

        # Enforce 1 câmera por linha (se mudou)
        if final_linha_id != cam.linha_id:
            cur.execute("SELECT id FROM cameras WHERE linha_id = ? AND id <> ?", (final_linha_id, camera_id))
            if cur.fetchone():
                raise HTTPException(status_code=400, detail="Já existe uma câmera cadastrada para esta linha")

    # Demais campos
    if body.porta is not None:
        final_porta = body.porta
    if body.resolucao_width is not None:
        final_rw = body.resolucao_width
    if body.resolucao_height is not None:
        final_rh = body.resolucao_height
    if body.fps is not None:
        final_fps = body.fps
    if body.ativo is not None:
        final_ativo = bool(body.ativo)
    if body.config_json is not None:
        final_cfg = body.config_json

    # Atualizar no banco
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE cameras
            SET nome = ?, bancada = ?, linha_id = ?, device_index = ?, ip_address = ?, porta = ?,
                resolucao_width = ?, resolucao_height = ?, fps = ?, config_json = ?, ativo = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                final_nome, final_bancada, final_linha_id, final_device_index, final_ip, final_porta,
                final_rw, final_rh, final_fps, json.dumps(final_cfg or {}), 1 if final_ativo else 0,
                camera_id,
            )
        )
        conn.commit()

    updated = db.get_camera(camera_id)
    return {
        "message": "Câmera atualizada com sucesso",
        "camera": updated.model_dump() if hasattr(updated, 'model_dump') else updated.dict(),
    }

@router.put("/{camera_id}/identificacao", summary="Atualiza ip_address e/ou bancada da câmera")
async def update_camera_identificacao(camera_id: int, body: CameraIdentificacaoUpdate):
    from central_manager.database.connection import DatabaseManager
    db = DatabaseManager()

    cam = db.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Câmera {camera_id} não encontrada")

    updates = []
    params = []

    # Validar e preparar bancada
    if body.bancada is not None:
        b = str(body.bancada).strip().upper()
        if b not in ("A", "B"):
            raise HTTPException(status_code=400, detail="bancada deve ser 'A' ou 'B'")
        updates.append("bancada = ?")
        params.append(b)

    # Validar e preparar ip_address
    if body.ip_address is not None:
        ip = str(body.ip_address).strip()
        if ip == "":
            # Limpar IP
            updates.append("ip_address = NULL")
        else:
            is_url = ip.startswith("rtsp://") or ip.startswith("http://") or ip.startswith("https://")
            is_ipv4 = bool(re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", ip))
            if not (is_url or is_ipv4):
                raise HTTPException(status_code=400, detail="ip_address deve ser IPv4 ou URL RTSP/HTTP")
            # Garantir unicidade de IP (quando definido)
            with db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id FROM cameras WHERE ip_address = ? AND id <> ?", (ip, camera_id))
                row = cur.fetchone()
                if row:
                    raise HTTPException(status_code=400, detail="ip_address já está em uso por outra câmera")
            updates.append("ip_address = ?")
            params.append(ip)

    if not updates:
        raise HTTPException(status_code=400, detail="Nada para atualizar")

    with db.get_connection() as conn:
        cur = conn.cursor()
        sql = f"UPDATE cameras SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        cur.execute(sql, (*params, camera_id))
        conn.commit()

    updated = db.get_camera(camera_id)
    return {
        "message": "Identificação atualizada com sucesso",
        "camera": updated.model_dump() if hasattr(updated, 'model_dump') else updated.dict()
    }

@router.get("/{camera_id}/status", summary="Obtém o status detalhado de uma câmera")
async def get_camera_status(camera_id: int, request: Request):
    """Retorna status detalhado de uma câmera específica."""
    orchestrator = request.app.state.orchestrator
    # Acesso correto ao DatabaseManager
    from central_manager.database.connection import DatabaseManager
    db_manager = DatabaseManager()

    db_camera = db_manager.get_camera(camera_id)
    if not db_camera:
        raise HTTPException(status_code=404, detail=f"Câmera com ID {camera_id} não encontrada no banco.")

    camera_source = db_camera.device_index if db_camera.device_index is not None else db_camera.ip_address

    # O método correto é get_camera_data
    camera_data = orchestrator.get_camera_data(camera_source)
    
    if not camera_data or not camera_data.running:
        return {
            "id": camera_source,
            "running": False,
            "message": "Câmera não encontrada ou inativa"
        }

    # Se chegou aqui, a câmera está ativa
    state_manager = camera_data.state_manager
    status_message = {}

    # Preferencialmente usa get_status() se disponível
    if hasattr(state_manager, 'get_status'):
        try:
            status_message = state_manager.get_status()
        except Exception:
            status_message = {"message": "Falha ao obter status via get_status()"}
    elif hasattr(state_manager, 'get_status_message'):
        status_message = state_manager.get_status_message()
    elif hasattr(state_manager, 'get_current_status'):
        current_status = state_manager.get_current_status()
        # Garante que o status seja sempre um dicionário para consistência da API
        if isinstance(current_status, str):
            status_message = {"message": current_status}
        elif isinstance(current_status, dict):
            status_message = current_status
        else:
            status_message = {"message": "Status em formato desconhecido."}
    else:
        status_message = {"message": "Método de status não encontrado no state manager."}
    
    return {
        "id": camera_source,  # mantém compatibilidade: id == source
        "camera_id": camera_id,
        "source": camera_source,
        "running": camera_data.running,
        "fps": getattr(camera_data, 'fps', 0),
        "status_message": status_message,
        "last_update": status_message.get('timestamp') if isinstance(status_message, dict) else None
    }

@router.delete("/{camera_id}", summary="Remove uma câmera")
async def delete_camera(camera_id: int, request: Request):
    """Remove uma câmera do banco e para o processador se estiver rodando."""
    from central_manager.database.connection import DatabaseManager
    db = DatabaseManager()

    cam = db.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Câmera {camera_id} não encontrada")

    # Tentar parar o processador se estiver ativo
    try:
        orchestrator = request.app.state.orchestrator
        orchestrator.stop_processor(camera_id)
    except Exception:
        # Ignorar erros ao parar (ex.: não estava rodando)
        pass

    # Remover do banco
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM cameras WHERE id = ?", (camera_id,))
        conn.commit()

    return {"success": True, "message": f"Câmera {camera_id} removida com sucesso"}

@router.post("/rescan")
async def rescan_cameras(request: Request):
    """Força uma nova busca por câmeras disponíveis."""
    try:
        orchestrator = request.app.state.orchestrator
        result = orchestrator.rescan_cameras()
        
        return {
            "success": True,
            "message": "Rebusca de câmeras concluída com sucesso",
            "data": result
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erro durante rebusca de câmeras: {str(e)}"
        )

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

@router.put("/{camera_id}/produto")
async def update_camera_produto(camera_id: int, body: ProdutoUpdate, request: Request):
    """Atualiza o produto (modelo) associado a uma câmera.

    - Atualiza o campo produto_id da câmera no banco
    - Se o processador estiver rodando, atualiza também product_id/name no processor
    - Aplica modelos YOLO e thresholds conforme produto.config_json (se presentes)
    """
    from central_manager.database.connection import DatabaseManager
    db = DatabaseManager()

    cam = db.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Câmera {camera_id} não encontrada")

    produto = db.get_produto(body.produto_id)
    if not produto:
        raise HTTPException(status_code=404, detail=f"Produto {body.produto_id} não encontrado")

    # Atualiza no banco
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE cameras SET produto_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (body.produto_id, camera_id),
        )
        conn.commit()
        # Ler campos adicionais do produto diretamente (itens_por_camada, max_camadas e config_json)
        cur.execute(
            """
            SELECT itens_por_camada, max_camadas, confidence_threshold, divisor_confidence, divisor_low_confidence, config_json
            FROM produtos WHERE id = ?
            """,
            (body.produto_id,)
        )
        row = cur.fetchone()

    # Resolver config_json e preparar fallbacks vindos de colunas do DB
    cfg = {}
    if row is not None:
        raw_cfg = row[5] if isinstance(row, tuple) else row['config_json']
        try:
            cfg = json.loads(raw_cfg) if isinstance(raw_cfg, str) else (raw_cfg or {})
        except Exception:
            cfg = {}

    item_model = cfg.get('item_model')
    roi_model = cfg.get('roi_model')
    requires_divisor = bool(cfg.get('requires_divisor', True))

    # Fallbacks a partir das colunas legadas
    fallback_conf_item = None
    fallback_conf_div = None
    fallback_conf_roi = None
    if row is not None:
        try:
            # row pode ser sqlite3.Row
            fallback_conf_item = row['confidence_threshold']
            # Preferir low_confidence como limiar principal do divisor; se ausente, usar divisor_confidence
            fallback_conf_div = row['divisor_low_confidence'] if row['divisor_low_confidence'] is not None else row['divisor_confidence']
            # Usar confidence_threshold como fallback do ROI também, na falta de conf_roi
            fallback_conf_roi = row['confidence_threshold']
        except Exception:
            try:
                # row como tupla: (itens_por_camada, max_camadas, confidence_threshold, divisor_confidence, divisor_low_confidence, config_json)
                fallback_conf_item = row[2]
                fallback_conf_div = row[4] if row[4] is not None else row[3]
                fallback_conf_roi = row[2]
            except Exception:
                pass

    # Prioriza config_json; aplica fallbacks das colunas quando ausentes
    conf_roi = cfg.get('conf_roi', fallback_conf_roi)
    conf_item = cfg.get('conf_item', fallback_conf_item)
    conf_div = cfg.get('conf_divisor', fallback_conf_div)

    itens_por_camada = None
    max_camadas = None
    if row is not None:
        # row could be sqlite3.Row or tuple depending on row_factory, but earlier we set row_factory=sqlite3.Row
        try:
            itens_por_camada = row['itens_por_camada']
            max_camadas = row['max_camadas']
        except Exception:
            try:
                itens_por_camada = row[0]
                max_camadas = row[1]
            except Exception:
                pass

    # Reflete no processador, se ativo
    orchestrator = request.app.state.orchestrator
    camera_source = cam.device_index if cam.device_index is not None else cam.ip_address
    processor = orchestrator.get_camera_data(camera_source)

    applied_models = {}
    applied_thresholds = {}
    applied_perfil = {}

    if processor:
        try:
            processor.product_id = body.produto_id
            processor.product_name = produto.nome
        except Exception:
            pass
        
        # Recarregar modelos YOLO conforme config_json
        try:
            if hasattr(processor, 'detector'):
                if item_model or roi_model:
                    applied_models = processor.detector.reload_models(
                        item_model_name=item_model,
                        roi_model_name=roi_model
                    )
                if any(v is not None for v in (conf_roi, conf_item, conf_div)):
                    applied_thresholds = processor.detector.apply_thresholds(
                        confianca_roi=conf_roi,
                        confianca_item=conf_item,
                        confianca_divisor=conf_div
                    )
        except Exception as e:
            # Não falha a requisição por erro de recarregar modelos
            applied_models['error'] = str(e)
        
        # Ajustar perfil de caixa e flags simples
        try:
            sm = getattr(processor, 'state_manager', None)
            if sm:
                if itens_por_camada:
                    sm.PERFIL_CAIXA['itens_por_camada'] = int(itens_por_camada)
                if max_camadas:
                    sm.PERFIL_CAIXA['total_camadas'] = int(max_camadas)
                # Flag de validação por divisor (desliga quando produto não exige divisor)
                if 'config' in sm.__dict__ and isinstance(sm.config, dict):
                    sm.config['usar_validacao_divisor_salto'] = bool(requires_divisor)
                applied_perfil = {
                    'itens_por_camada': sm.PERFIL_CAIXA.get('itens_por_camada'),
                    'total_camadas': sm.PERFIL_CAIXA.get('total_camadas'),
                    'requires_divisor': requires_divisor
                }
        except Exception:
            pass

    return {
        "message": "Produto da câmera atualizado com sucesso",
        "camera_id": camera_id,
        "produto_id": body.produto_id,
        "produto_nome": produto.nome,
        "applied_models": applied_models,
        "applied_thresholds": applied_thresholds,
        "perfil_aplicado": applied_perfil,
    }

@router.get("/{camera_id}/models", summary="Modelos YOLO e thresholds ativos para a câmera")
async def get_camera_models(camera_id: int, request: Request):
    from central_manager.database.connection import DatabaseManager
    db = DatabaseManager()

    cam = db.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Câmera {camera_id} não encontrada")

    # Fallback via produto/config_json no DB
    prod = db.get_produto(cam.produto_id) if cam.produto_id else None
    cfg = {}
    if prod and getattr(prod, 'config_json', None):
        try:
            cfg = json.loads(prod.config_json) if isinstance(prod.config_json, str) else (prod.config_json or {})
        except Exception:
            cfg = {}

    item_model_cfg = cfg.get('item_model')
    roi_model_cfg = cfg.get('roi_model')
    conf_roi_cfg = cfg.get('conf_roi')
    conf_item_cfg = cfg.get('conf_item')
    conf_div_cfg = cfg.get('conf_divisor')
    requires_divisor_cfg = bool(cfg.get('requires_divisor', True))

    orchestrator = request.app.state.orchestrator
    source = cam.device_index if cam.device_index is not None else cam.ip_address
    processor = orchestrator.get_camera_data(source)

    runtime = False
    item_model = item_model_cfg
    roi_model = roi_model_cfg
    thresholds = {
        "confianca_roi": conf_roi_cfg,
        "confianca_item": conf_item_cfg,
        "confianca_divisor": conf_div_cfg,
    }
    perfil = {}
    requires_divisor = requires_divisor_cfg

    if processor and getattr(processor, 'running', False) and hasattr(processor, 'detector'):
        runtime = True
        det = processor.detector
        try:
            item_model = os.path.basename(getattr(det, 'item_model_path', '') or item_model_cfg)
            roi_model = os.path.basename(getattr(det, 'roi_model_path', '') or roi_model_cfg)
            thresholds = {
                "confianca_roi": getattr(det, 'confianca_roi', conf_roi_cfg),
                "confianca_item": getattr(det, 'confianca_item', conf_item_cfg),
                "confianca_divisor": getattr(det, 'confianca_divisor', conf_div_cfg),
            }
        except Exception:
            pass
        sm = getattr(processor, 'state_manager', None)
        # Adiciona chaves avançadas a partir do config do StateManager em runtime
        try:
            if sm and isinstance(getattr(sm, 'config', None), dict):
                thresholds.update({
                    "percentual_itens_novos_salto": sm.config.get('percentual_itens_novos_salto'),
                    "percentual_itens_novos_minimo": sm.config.get('percentual_itens_novos_minimo'),
                    "usar_validacao_divisor_salto": sm.config.get('usar_validacao_divisor_salto'),
                    "tempo_divisor_estavel_minimo": sm.config.get('tempo_divisor_estavel_minimo'),
                    "tempo_maximo_instabilidade_divisor": sm.config.get('tempo_maximo_instabilidade_divisor'),
                })
        except Exception:
            pass
        if sm and hasattr(sm, 'PERFIL_CAIXA'):
            perfil = {
                "itens_por_camada": sm.PERFIL_CAIXA.get('itens_por_camada'),
                "total_camadas": sm.PERFIL_CAIXA.get('total_camadas'),
            }
            try:
                if isinstance(getattr(sm, 'config', None), dict):
                    requires_divisor = bool(sm.config.get('usar_validacao_divisor_salto', requires_divisor_cfg))
            except Exception:
                pass
    else:
        # Não está em runtime: incluir defaults do STATE_CONFIG para que o frontend renderize "Avançado"
        try:
            from central_manager.core_advanced.config import STATE_CONFIG
            thresholds.update({
                "percentual_itens_novos_salto": STATE_CONFIG.get('percentual_itens_novos_salto'),
                "percentual_itens_novos_minimo": STATE_CONFIG.get('percentual_itens_novos_minimo'),
                "usar_validacao_divisor_salto": STATE_CONFIG.get('usar_validacao_divisor_salto'),
                "tempo_divisor_estavel_minimo": STATE_CONFIG.get('tempo_divisor_estavel_minimo'),
                "tempo_maximo_instabilidade_divisor": STATE_CONFIG.get('tempo_maximo_instabilidade_divisor'),
            })
        except Exception:
            pass

    return {
        "camera_id": camera_id,
        "source": source,
        "runtime": runtime,
        "item_model": item_model,
        "roi_model": roi_model,
        "thresholds": thresholds,
        "perfil_caixa": perfil,
        "requires_divisor": requires_divisor,
    }

@router.put("/{camera_id}/thresholds", summary="Aplica thresholds no detector ativo da câmera")
async def update_camera_thresholds(camera_id: int, body: ThresholdsUpdate, request: Request):
    """Atualiza limiares de confiança (ROI, Item, Divisor) no detector ativo em runtime.

    Não persiste no banco. Para resetar, reaplique o produto com PUT /cameras/{id}/produto.
    """
    from central_manager.database.connection import DatabaseManager
    db = DatabaseManager()

    cam = db.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Câmera {camera_id} não encontrada")

    source = cam.device_index if cam.device_index is not None else cam.ip_address
    orchestrator = request.app.state.orchestrator
    processor = orchestrator.get_camera_data(source)

    if not processor or not getattr(processor, 'running', False) or not hasattr(processor, 'detector'):
        raise HTTPException(status_code=400, detail="Câmera inativa ou detector indisponível")

    det = processor.detector
    applied = det.apply_thresholds(
        confianca_roi=body.confianca_roi,
        confianca_item=body.confianca_item,
        confianca_divisor=body.confianca_divisor,
    )
    # Aplicar chaves avançadas no StateManager em runtime
    state_applied = {}
    sm = getattr(processor, 'state_manager', None)
    try:
        if sm and isinstance(getattr(sm, 'config', None), dict):
            # Evitar efeitos colaterais entre instâncias
            try:
                sm.config = dict(sm.config)
            except Exception:
                pass
            # percentual_itens_novos_salto (clamp 0..1)
            if body.percentual_itens_novos_salto is not None:
                try:
                    v = float(body.percentual_itens_novos_salto)
                    if v < 0.0: v = 0.0
                    if v > 1.0: v = 1.0
                    sm.config['percentual_itens_novos_salto'] = v
                    state_applied['percentual_itens_novos_salto'] = v
                except Exception:
                    pass
            # percentual_itens_novos_minimo (clamp 0..1)
            if body.percentual_itens_novos_minimo is not None:
                try:
                    v = float(body.percentual_itens_novos_minimo)
                    if v < 0.0: v = 0.0
                    if v > 1.0: v = 1.0
                    sm.config['percentual_itens_novos_minimo'] = v
                    state_applied['percentual_itens_novos_minimo'] = v
                except Exception:
                    pass
            # usar_validacao_divisor_salto (bool)
            if body.usar_validacao_divisor_salto is not None:
                try:
                    b = bool(body.usar_validacao_divisor_salto)
                    sm.config['usar_validacao_divisor_salto'] = b
                    state_applied['usar_validacao_divisor_salto'] = b
                except Exception:
                    pass
            # tempo_divisor_estavel_minimo (>= 0)
            if body.tempo_divisor_estavel_minimo is not None:
                try:
                    v = float(body.tempo_divisor_estavel_minimo)
                    if v < 0.0: v = 0.0
                    sm.config['tempo_divisor_estavel_minimo'] = v
                    state_applied['tempo_divisor_estavel_minimo'] = v
                except Exception:
                    pass
            # tempo_maximo_instabilidade_divisor (>= 0)
            if body.tempo_maximo_instabilidade_divisor is not None:
                try:
                    v = float(body.tempo_maximo_instabilidade_divisor)
                    if v < 0.0: v = 0.0
                    sm.config['tempo_maximo_instabilidade_divisor'] = v
                    state_applied['tempo_maximo_instabilidade_divisor'] = v
                except Exception:
                    pass
    except Exception:
        pass
    runtime_thresholds = {
        "confianca_roi": getattr(det, 'confianca_roi', None),
        "confianca_item": getattr(det, 'confianca_item', None),
        "confianca_divisor": getattr(det, 'confianca_divisor', None),
    }
    # Retornar também snapshot das chaves avançadas aplicadas
    try:
        if sm and isinstance(getattr(sm, 'config', None), dict):
            runtime_thresholds.update({
                "percentual_itens_novos_salto": sm.config.get('percentual_itens_novos_salto'),
                "percentual_itens_novos_minimo": sm.config.get('percentual_itens_novos_minimo'),
                "usar_validacao_divisor_salto": sm.config.get('usar_validacao_divisor_salto'),
                "tempo_divisor_estavel_minimo": sm.config.get('tempo_divisor_estavel_minimo'),
                "tempo_maximo_instabilidade_divisor": sm.config.get('tempo_maximo_instabilidade_divisor'),
            })
    except Exception:
        pass

    return {
        "camera_id": camera_id,
        "source": source,
        "applied": applied,
        "state_applied": state_applied,
        "runtime_thresholds": runtime_thresholds,
    }
