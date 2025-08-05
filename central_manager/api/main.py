"""
FastAPI Central Manager - SIAC Industrial
API principal para controle centralizado do sistema
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime
import asyncio

# Imports do projeto
import sys
import os

# Add parent directory to path for absolute imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from database.connection import DatabaseManager
from camera_system.camera_manager import CameraManager
from siac_integration import get_siac_manager, SiacStatus
from models.database_models import (
    # Create Models
    SetorCreate, LinhaCreate, ProdutoCreate, CameraCreate,
    ProducaoDadosCreate, AlertaHistoricoCreate,
    
    # Response Models
    Setor, Linha, Produto, Camera, ProducaoDados, AlertaHistorico,
    StatusResponse, DashboardResponse, MetricasResponse,
    
    # Enums
    StatusEnum, EstadoProducaoEnum, SeveridadeEnum
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Gerenciadores globais
db_manager: DatabaseManager = None
camera_manager: CameraManager = None
siac_manager = get_siac_manager()
websocket_connections: Dict[str, WebSocket] = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia ciclo de vida da aplicação"""
    global db_manager, camera_manager
    
    # Startup
    logger.info("Iniciando SIAC Central Manager...")
    
    try:
        # Inicializar banco de dados
        db_manager = DatabaseManager()
        logger.info("Database Manager inicializado")
        
        # Inicializar gerenciador de câmeras
        camera_manager = CameraManager(max_cameras=8)
        
        # Configurar callbacks do camera manager
        camera_manager.set_detection_callback(on_camera_detection)
        camera_manager.set_status_callback(on_camera_status_change)
        camera_manager.set_alert_callback(on_camera_alert)
        
        logger.info("Camera Manager inicializado")
        
        # Carregar câmeras existentes do banco
        await load_cameras_from_database()
        
        logger.info("SIAC Central Manager iniciado com sucesso!")
        
    except Exception as e:
        logger.error(f"Erro ao inicializar sistema: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Finalizando SIAC Central Manager...")
    
    try:
        if camera_manager:
            camera_manager.stop_all_cameras()
        
        # Fechar conexões WebSocket
        for ws in websocket_connections.values():
            try:
                await ws.close()
            except:
                pass
        
        logger.info("Sistema finalizado")
        
    except Exception as e:
        logger.error(f"Erro ao finalizar sistema: {e}")

# Criar aplicação FastAPI
app = FastAPI(
    title="SIAC Industrial Central Manager",
    description="Sistema centralizado de controle para contagem de itens industriais",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================
# CALLBACKS DO CAMERA MANAGER
# =====================================================

def on_camera_detection(result: Dict):
    """Callback para detecções de câmera"""
    try:
        # Salvar dados de produção no banco
        camera_id = result.get('camera_id')
        if camera_id and db_manager:
            
            # Criar dados de produção
            dados = ProducaoDadosCreate(
                camera_id=camera_id,
                estado=EstadoProducaoEnum(result.get('estado', 'AGUARDANDO_CAIXA')),
                contagem_atual=result.get('contagem_atual', 0),
                camada_atual=result.get('camada_atual', 1),
                caixas_completas=result.get('caixas_completas', 0),
                roi_detectada=result.get('roi_detectada', False),
                itens_detectados=result.get('itens_detectados', 0),
                divisores_detectados=result.get('divisores_detectados', 0),
                fps_atual=result.get('fps_atual'),
                tempo_processamento=result.get('tempo_processamento'),
                dados_json=result
            )
            
            db_manager.create_producao_dados(dados)
        
        # Enviar para WebSocket
        asyncio.create_task(broadcast_to_websockets({
            'type': 'detection',
            'data': result,
            'timestamp': datetime.now().isoformat()
        }))
        
    except Exception as e:
        logger.error(f"Erro no callback de detecção: {e}")

def on_camera_status_change(camera_id: int, status: Dict):
    """Callback para mudanças de status"""
    try:
        # Atualizar status no banco
        if db_manager:
            status_enum = StatusEnum(status.get('status', 'offline'))
            db_manager.update_camera_status(camera_id, status_enum)
        
        # Enviar para WebSocket
        asyncio.create_task(broadcast_to_websockets({
            'type': 'status_change',
            'camera_id': camera_id,
            'data': status,
            'timestamp': datetime.now().isoformat()
        }))
        
    except Exception as e:
        logger.error(f"Erro no callback de status: {e}")

def on_camera_alert(camera_id: int, alert: Dict):
    """Callback para alertas"""
    try:
        # Salvar alerta no banco
        if db_manager:
            alerta = AlertaHistoricoCreate(
                camera_id=camera_id,
                tipo=alert.get('tipo', 'sistema'),
                severidade=SeveridadeEnum(alert.get('severidade', 'warning')),
                mensagem=alert.get('mensagem', ''),
                estado_anterior=alert.get('estado_anterior'),
                estado_atual=alert.get('estado_atual'),
                contagem_atual=alert.get('contagem_atual'),
                camada_atual=alert.get('camada_atual'),
                dados_json=alert
            )
            
            db_manager.create_alerta(alerta)
        
        # Enviar para WebSocket
        asyncio.create_task(broadcast_to_websockets({
            'type': 'alert',
            'camera_id': camera_id,
            'data': alert,
            'timestamp': datetime.now().isoformat()
        }))
        
    except Exception as e:
        logger.error(f"Erro no callback de alerta: {e}")

async def broadcast_to_websockets(message: Dict):
    """Envia mensagem para todos os WebSockets conectados"""
    if not websocket_connections:
        return
    
    message_str = json.dumps(message)
    disconnected = []
    
    for client_id, websocket in websocket_connections.items():
        try:
            await websocket.send_text(message_str)
        except:
            disconnected.append(client_id)
    
    # Remover conexões desconectadas
    for client_id in disconnected:
        websocket_connections.pop(client_id, None)

async def load_cameras_from_database():
    """Carrega câmeras existentes do banco para o camera manager"""
    try:
        if not db_manager:
            return
        
        # Buscar todas as câmeras ativas
        cameras = []
        setores = db_manager.get_setores()
        
        for setor in setores:
            linhas = db_manager.get_linhas_by_setor(setor.id)
            for linha in linhas:
                cameras_linha = db_manager.get_cameras_by_linha(linha.id)
                cameras.extend(cameras_linha)
        
        # Adicionar câmeras ao camera manager
        for camera in cameras:
            if camera.ativo:
                # Buscar produto associado
                produto = None
                if camera.produto_id:
                    produto = db_manager.get_produto(camera.produto_id)
                
                # Configurar câmera
                camera_config = {
                    'device_index': camera.device_index,
                    'ip_address': camera.ip_address,
                    'porta': camera.porta,
                    'resolucao_width': camera.resolucao_width,
                    'resolucao_height': camera.resolucao_height,
                    'fps': camera.fps,
                    'produto_id': camera.produto_id,
                    'config_json': camera.config_json
                }
                
                # Adicionar ao camera manager
                success = camera_manager.add_camera(camera.id, camera_config)
                if success:
                    logger.info(f"Câmera {camera.nome} (ID: {camera.id}) carregada")
                else:
                    logger.warning(f"Falha ao carregar câmera {camera.nome} (ID: {camera.id})")
        
        logger.info(f"Carregadas {len(cameras)} câmeras do banco de dados")
        
    except Exception as e:
        logger.error(f"Erro ao carregar câmeras do banco: {e}")

# =====================================================
# ROTAS DE STATUS E DASHBOARD
# =====================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Página inicial com informações básicas"""
    return """
    <html>
        <head>
            <title>SIAC Industrial Central Manager</title>
        </head>
        <body>
            <h1>🏭 SIAC Industrial Central Manager</h1>
            <p>Sistema centralizado de controle para contagem de itens industriais</p>
            
            <h2>📊 APIs Disponíveis:</h2>
            <ul>
                <li><a href="/docs">📚 Documentação Swagger</a></li>
                <li><a href="/status">📈 Status do Sistema</a></li>
                <li><a href="/dashboard">🎛️ Dashboard</a></li>
                <li><a href="/setores">🏢 Setores</a></li>
                <li><a href="/cameras">📹 Câmeras</a></li>
            </ul>
            
            <h2>🔌 WebSocket:</h2>
            <p>Conecte em: <code>ws://localhost:8000/ws/{client_id}</code></p>
        </body>
    </html>
    """

@app.get("/status", response_model=StatusResponse)
async def get_status():
    """Retorna status geral do sistema"""
    try:
        # Contar câmeras
        cameras_status = camera_manager.get_all_status() if camera_manager else {}
        cameras_total = cameras_status.get('cameras_count', 0)
        cameras_ativas = cameras_status.get('cameras_active', 0)
        
        # Contar alertas pendentes
        alertas_pendentes = 0
        if db_manager:
            alertas_recentes = db_manager.get_alertas_recentes(limit=100)
            alertas_pendentes = len([a for a in alertas_recentes if not a.resolvido])
        
        # Calcular uptime
        uptime = "0:00:00"
        if camera_manager and hasattr(camera_manager, 'start_time') and camera_manager.start_time:
            import time
            uptime_seconds = time.time() - camera_manager.start_time
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            seconds = int(uptime_seconds % 60)
            uptime = f"{hours}:{minutes:02d}:{seconds:02d}"
        
        siac_status = siac_manager.get_status()
        
        return StatusResponse(
            sistema_online=camera_manager.running if camera_manager else False,
            cameras_ativas=cameras_ativas,
            cameras_total=cameras_total,
            alertas_pendentes=alertas_pendentes,
            caixas_completas_hoje=0,  # TODO: Implementar contagem diária
            uptime=uptime,
            siac_status=siac_status
        )
        
    except Exception as e:
        logger.error(f"Erro ao obter status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard():
    """Retorna dados completos do dashboard"""
    try:
        # Status geral
        status = await get_status()
        
        # Dados do banco
        setores = db_manager.get_setores() if db_manager else []
        linhas_ativas = []
        cameras_status = []
        alertas_recentes = []
        
        if db_manager:
            # Buscar linhas ativas
            for setor in setores:
                linhas = db_manager.get_linhas_by_setor(setor.id)
                linhas_ativas.extend(linhas)
            
            # Buscar câmeras
            for linha in linhas_ativas:
                cameras = db_manager.get_cameras_by_linha(linha.id)
                cameras_status.extend(cameras)
            
            # Alertas recentes
            alertas_recentes = db_manager.get_alertas_recentes(limit=10)
        
        return DashboardResponse(
            status=status,
            setores=setores,
            linhas_ativas=linhas_ativas,
            cameras_status=cameras_status,
            alertas_recentes=alertas_recentes
        )
        
    except Exception as e:
        logger.error(f"Erro ao obter dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# ROTAS CRUD - SETORES
# =====================================================

@app.get("/setores", response_model=List[Setor])
async def get_setores():
    """Lista todos os setores"""
    try:
        return db_manager.get_setores()
    except Exception as e:
        logger.error(f"Erro ao buscar setores: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/setores", response_model=Setor)
async def create_setor(setor: SetorCreate):
    """Cria um novo setor"""
    try:
        return db_manager.create_setor(setor)
    except Exception as e:
        logger.error(f"Erro ao criar setor: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/setores/{setor_id}", response_model=Setor)
async def get_setor(setor_id: int):
    """Busca setor por ID"""
    try:
        setor = db_manager.get_setor(setor_id)
        if not setor:
            raise HTTPException(status_code=404, detail="Setor não encontrado")
        return setor
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar setor {setor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# ROTAS CRUD - LINHAS
# =====================================================

@app.post("/linhas", response_model=Linha)
async def create_linha(linha: LinhaCreate):
    """Cria uma nova linha"""
    try:
        return db_manager.create_linha(linha)
    except Exception as e:
        logger.error(f"Erro ao criar linha: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/setores/{setor_id}/linhas", response_model=List[Linha])
async def get_linhas_by_setor(setor_id: int):
    """Lista linhas de um setor"""
    try:
        return db_manager.get_linhas_by_setor(setor_id)
    except Exception as e:
        logger.error(f"Erro ao buscar linhas do setor {setor_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# ROTAS CRUD - PRODUTOS
# =====================================================

@app.get("/produtos", response_model=List[Produto])
async def get_produtos():
    """Lista todos os produtos"""
    try:
        return db_manager.get_produtos()
    except Exception as e:
        logger.error(f"Erro ao buscar produtos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/produtos", response_model=Produto)
async def create_produto(produto: ProdutoCreate):
    """Cria um novo produto"""
    try:
        return db_manager.create_produto(produto)
    except Exception as e:
        logger.error(f"Erro ao criar produto: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# ROTAS CRUD - CAMERAS
# =====================================================

@app.get("/cameras", response_model=List[Camera])
async def get_cameras():
    """Lista todas as câmeras"""
    try:
        cameras = []
        setores = db_manager.get_setores()
        
        for setor in setores:
            linhas = db_manager.get_linhas_by_setor(setor.id)
            for linha in linhas:
                cameras_linha = db_manager.get_cameras_by_linha(linha.id)
                cameras.extend(cameras_linha)
        
        return cameras
    except Exception as e:
        logger.error(f"Erro ao buscar câmeras: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cameras", response_model=Camera)
async def create_camera(camera: CameraCreate):
    """Cria uma nova câmera"""
    try:
        # Criar no banco
        new_camera = db_manager.create_camera(camera)
        
        # Adicionar ao camera manager se ativa
        if new_camera.ativo and camera_manager:
            camera_config = {
                'device_index': new_camera.device_index,
                'ip_address': new_camera.ip_address,
                'porta': new_camera.porta,
                'resolucao_width': new_camera.resolucao_width,
                'resolucao_height': new_camera.resolucao_height,
                'fps': new_camera.fps,
                'produto_id': new_camera.produto_id,
                'config_json': new_camera.config_json
            }
            
            success = camera_manager.add_camera(new_camera.id, camera_config)
            if not success:
                logger.warning(f"Falha ao adicionar câmera {new_camera.id} ao camera manager")
        
        return new_camera
        
    except Exception as e:
        logger.error(f"Erro ao criar câmera: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cameras/{camera_id}/status")
async def get_camera_status(camera_id: int):
    """Retorna status de uma câmera específica"""
    try:
        if not camera_manager:
            raise HTTPException(status_code=503, detail="Camera manager não disponível")
        
        status = camera_manager.get_camera_status(camera_id)
        if not status:
            raise HTTPException(status_code=404, detail="Câmera não encontrada")
        
        return status
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao buscar status da câmera {camera_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================
# WEBSOCKET
# =====================================================

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket para comunicação em tempo real"""
    await websocket.accept()
    websocket_connections[client_id] = websocket
    
    logger.info(f"Cliente {client_id} conectado via WebSocket")
    
    try:
        # Enviar status inicial
        status = await get_status()
        await websocket.send_text(json.dumps({
            'type': 'status',
            'data': status.model_dump(),
            'timestamp': datetime.now().isoformat()
        }))
        
        # Manter conexão viva
        while True:
            try:
                # Aguardar mensagens do cliente (ping/pong)
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get('type') == 'ping':
                    await websocket.send_text(json.dumps({
                        'type': 'pong',
                        'timestamp': datetime.now().isoformat()
                    }))
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Erro no WebSocket {client_id}: {e}")
                break
    
    finally:
        websocket_connections.pop(client_id, None)
        logger.info(f"Cliente {client_id} desconectado")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
