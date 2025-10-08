import threading
from queue import Queue
from threading import Thread, Event
from typing import Dict, List, Optional, Any
import json

from .camera_processor import CameraProcessor
from ..core_simple.state_manager_simple import StateManagerSimple as SimpleStateManager
from .simple_logger import SimpleLogger
from ..database.connection import DatabaseManager


class Orchestrator:
    """Gerencia múltiplos processadores de câmera em threads separadas."""

    def __init__(self, alert_manager: 'AlertManager'):
        self.logger = SimpleLogger("Orchestrator")
        self.logger.info("--- INICIALIZANDO ORQUESTRADOR ---")
        try:
            self.is_running = False
            self.camera_processors: Dict[Any, CameraProcessor] = {}
            self.camera_threads: Dict[Any, threading.Thread] = {}
            self.lock = threading.Lock()
            self.db_manager = DatabaseManager()
            self.alert_manager = alert_manager # Armazena a instância única
            self.logger.info("Orquestrador inicializado com sucesso.")
        except Exception as e:
            self.logger.error(f"Falha crítica ao inicializar o Orquestrador: {e}", exc_info=True)
            raise  # Re-levanta a exceção para impedir a inicialização

    def _discover_cameras(self) -> List[Any]:
        """Busca câmeras ativas no banco de dados."""
        self.logger.info("Buscando câmeras ativas no banco de dados...")
        try:
            # A fonte da verdade agora é o banco de dados
            db_cameras = self.db_manager.get_all_cameras(ativo_only=True)
            
            camera_sources = []
            for cam in db_cameras:
                # Para câmeras USB, a fonte é o device_index
                if cam.device_index is not None:
                    camera_sources.append(cam.device_index)
                    self.logger.info(f"  -> Encontrada Câmera USB: ID {cam.id}, Índice {cam.device_index} ({cam.nome})")
                
                # Para câmeras IP, a fonte é a URL (a ser construída ou extraída)
                elif cam.ip_address:
                    # TODO: Construir a URL RTSP completa a partir dos campos do DB
                    # Por enquanto, vamos assumir que ip_address já é a URL
                    camera_sources.append(cam.ip_address)
                    self.logger.info(f"  -> Encontrada Câmera IP: ID {cam.id}, URL {cam.ip_address} ({cam.nome})")

            if not camera_sources:
                self.logger.warning("Nenhuma câmera ativa encontrada no banco de dados.")

            return camera_sources
        
        except Exception as e:
            self.logger.error(f"Erro ao buscar câmeras no banco de dados: {e}", exc_info=True)
            return []

    def add_camera(self, camera_source):
        """Adiciona uma nova câmera para ser gerenciada."""
        if camera_source in self.camera_processors:
            self.logger.warning(f"Aviso: Câmera {camera_source} já existe.")
            return

        # Determinar core (simple vs advanced) com base no perfil do produto (max_camadas)
        state_manager_cls = None
        try:
            db_cameras = self.db_manager.get_all_cameras(ativo_only=True)
            cam_row = None
            for c in db_cameras:
                src = c.device_index if c.device_index is not None else c.ip_address
                if str(src) == str(camera_source):
                    cam_row = c
                    break
            if cam_row and cam_row.produto_id:
                with self.db_manager.get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT max_camadas FROM produtos WHERE id = ?",
                        (cam_row.produto_id,),
                    )
                    row = cur.fetchone()
                max_camadas = None
                if row is not None:
                    max_camadas = row[0] if isinstance(row, tuple) else row.get('max_camadas')
                if max_camadas == 1:
                    state_manager_cls = SimpleStateManager
                    self.logger.info(f"[{camera_source}] Perfil x1 detectado: usando core_simple (StateManagerSimple)")
        except Exception as e:
            self.logger.warning(f"[{camera_source}] Não foi possível resolver perfil para escolha de core: {e}")

        output_queue = Queue(maxsize=2)  # Fila pequena para evitar latência
        processor = CameraProcessor(
            output_queue=output_queue,
            camera_source=camera_source,
            alert_manager=self.alert_manager,  # Passa a instância para o processador
            state_manager_cls=state_manager_cls,
        )
        
        self.camera_processors[camera_source] = processor
        self.logger.info(f"Processador para câmera {camera_source} adicionado.")

        # Auto-aplicar configuração do produto da câmera a partir do banco (modelos, thresholds, perfil)
        try:
            db_cameras = self.db_manager.get_all_cameras(ativo_only=True)
            cam_row = None
            for c in db_cameras:
                src = c.device_index if c.device_index is not None else c.ip_address
                if str(src) == str(camera_source):
                    cam_row = c
                    break
            if not cam_row:
                self.logger.warning(f"Config produto: câmera {camera_source} não encontrada no DB para aplicar configuração.")
                return

            produto = self.db_manager.get_produto(cam_row.produto_id) if cam_row.produto_id else None
            itens_por_camada = None
            max_camadas = None
            cfg = {}
            if produto:
                with self.db_manager.get_connection() as conn:
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT itens_por_camada, max_camadas, config_json FROM produtos WHERE id = ?",
                        (produto.id,)
                    )
                    row = cur.fetchone()
                if row is not None:
                    try:
                        itens_por_camada = row[0] if isinstance(row, tuple) else row['itens_por_camada']
                        max_camadas = row[1] if isinstance(row, tuple) else row['max_camadas']
                        raw_cfg = row[2] if isinstance(row, tuple) else row['config_json']
                        cfg = json.loads(raw_cfg) if isinstance(raw_cfg, str) else (raw_cfg or {})
                    except Exception:
                        cfg = {}

            # Atualiza identificação do produto no processor
            try:
                if produto:
                    processor.product_id = produto.id
                    processor.product_name = produto.nome
            except Exception:
                pass

            # Aplicar modelos e thresholds, se definidos
            try:
                det = getattr(processor, 'detector', None)
                if det and isinstance(cfg, dict):
                    item_model = cfg.get('item_model')
                    roi_model = cfg.get('roi_model')
                    if item_model or roi_model:
                        det.reload_models(item_model_name=item_model, roi_model_name=roi_model)
                        self.logger.info(f"[{camera_source}] Modelos aplicados no startup: item={item_model}, roi={roi_model}")
                    conf_roi = cfg.get('conf_roi')
                    conf_item = cfg.get('conf_item')
                    conf_div = cfg.get('conf_divisor')
                    if any(v is not None for v in (conf_roi, conf_item, conf_div)):
                        det.apply_thresholds(confianca_roi=conf_roi, confianca_item=conf_item, confianca_divisor=conf_div)
                        self.logger.info(f"[{camera_source}] Thresholds aplicados no startup: roi={conf_roi}, item={conf_item}, divisor={conf_div}")
            except Exception as e:
                self.logger.warning(f"[{camera_source}] Falha ao aplicar modelos/thresholds do produto no startup: {e}")

            # Aplicar perfil da caixa (itens_por_camada, total_camadas) e flags
            try:
                sm = getattr(processor, 'state_manager', None)
                if sm:
                    if itens_por_camada:
                        sm.PERFIL_CAIXA['itens_por_camada'] = int(itens_por_camada)
                    if max_camadas:
                        sm.PERFIL_CAIXA['total_camadas'] = int(max_camadas)
                    requires_divisor = bool(cfg.get('requires_divisor', True))
                    if 'config' in sm.__dict__ and isinstance(sm.config, dict):
                        sm.config['usar_validacao_divisor_salto'] = requires_divisor
                    self.logger.info(f"[{camera_source}] Perfil aplicado no startup: itens_por_camada={sm.PERFIL_CAIXA.get('itens_por_camada')}, total_camadas={sm.PERFIL_CAIXA.get('total_camadas')}, requires_divisor={requires_divisor}")
            except Exception as e:
                self.logger.warning(f"[{camera_source}] Falha ao aplicar perfil do produto no startup: {e}")
        except Exception as e:
            # Captura qualquer falha do bloco de configuração (try externo)
            self.logger.warning(
                f"[{camera_source}] Falha geral ao aplicar configuração do produto no startup: {e}",
                exc_info=True,
            )

    def start(self):
        """Inicia o orquestrador e o processamento das câmeras."""
        self.logger.info("--- INICIANDO PROCESSAMENTO DAS CÂMERAS ---")
        self.is_running = True
        cameras_to_process = self._discover_cameras()
        
        if not cameras_to_process:
            self.logger.warning("Nenhuma câmera para processar. O orquestrador continuará rodando em modo de espera.")
            return

        for source in cameras_to_process:
            self.add_camera(source)
            self._start_processor_thread(source)
        self.logger.info("Orquestrador iniciado e threads de câmera despachadas.")

    def _start_processor_thread(self, camera_source):
        """Inicia uma thread de processamento para uma câmera específica."""
        thread = threading.Thread(target=self.camera_processors[camera_source].run, daemon=True)
        self.camera_threads[camera_source] = thread
        thread.start()
        self.logger.info(f"Thread da câmera {camera_source} iniciada.")

    def rescan_cameras(self) -> Dict[str, Any]:
        """Para, limpa e redescobre as câmeras a partir do banco de dados."""
        self.logger.info("Iniciando rebusca manual de câmeras...")
        
        # 1. Parar processadores existentes
        self.stop_all_processors()

        # 2. Limpar listas
        with self.lock:
            self.camera_processors.clear()
            self.camera_threads.clear()
        self.logger.info("Processadores e threads antigos foram limpos.")

        # 3. Redescobrir câmeras a partir da fonte (agora o DB)
        cameras_to_process = self._discover_cameras()

        # 4. Reiniciar threads se o orquestrador estava rodando
        if self.is_running:
            self.logger.info("Reiniciando processamento para câmeras redescobertas...")
            for source in cameras_to_process:
                self.add_camera(source)
                self._start_processor_thread(source)

        result = {
            "status": "success",
            "message": "Rebusca de câmeras concluída.",
            "cameras_found": len(cameras_to_process),
            "camera_list": cameras_to_process
        }
        self.logger.info(f"Rebusca concluída. {result['cameras_found']} câmeras ativas.")
        return result

    def stop(self):
        """Para o orquestrador e todas as threads de câmera."""
        self.is_running = False
        self.stop_all_processors()

    def stop_all_processors(self):
        """Para todos os processadores e aguarda as threads finalizarem."""
        self.logger.info("Parando todos os processadores...")
        for processor in self.camera_processors.values():
            processor.stop()
        
        for thread in self.camera_threads.values():
            thread.join()
            self.logger.info(f"Thread da câmera finalizada.")

    def get_camera_data(self, camera_source):
        """Retorna os dados (processador e fila) de uma câmera específica."""
        return self.camera_processors.get(camera_source)

    def get_all_cameras_summary(self):
        """Retorna uma lista de resumos do estado de todas as câmeras."""
        return [
            processor.get_status()
            for processor in self.camera_processors.values()
        ]

    def get_registered_cameras(self):
        """Retorna lista de IDs das câmeras registradas no orquestrador."""
        return list(self.camera_processors.keys())

    # -----------------------------------------------------
    # Controle explícito por camera_id (tela Dashboard)
    # -----------------------------------------------------
    def _resolve_source_from_camera_id(self, camera_id: int):
        """Converte o camera_id do banco em camera_source (device_index ou ip/url)."""
        try:
            cam = self.db_manager.get_camera(int(camera_id))
            if not cam:
                self.logger.error(f"Câmera com ID {camera_id} não encontrada no banco.")
                return None
            return cam.device_index if cam.device_index is not None else cam.ip_address
        except Exception as e:
            self.logger.error(f"Erro ao resolver source da câmera {camera_id}: {e}")
            return None

    def start_processor(self, camera_id: int) -> bool:
        """Inicia o processador da câmera mapeando camera_id -> source."""
        source = self._resolve_source_from_camera_id(camera_id)
        if source is None:
            return False

        with self.lock:
            processor = self.camera_processors.get(source)
            thread = self.camera_threads.get(source)

            # Se não houver processor, cria um novo normalmente
            if processor is None:
                self.add_camera(source)
                processor = self.camera_processors.get(source)
                thread = self.camera_threads.get(source)

            # Reset de flags para permitir reinício após stop()
            try:
                if processor is not None:
                    processor.should_stop = False
                    processor.running = False
            except Exception:
                pass

            # Se já existir thread ativa, não crie dupla
            if thread is None or not thread.is_alive():
                self._start_processor_thread(source)
            else:
                self.logger.info(f"Thread da câmera {source} já está ativa.")
        return True

    def stop_processor(self, camera_id: int) -> bool:
        """Para o processador da câmera mapeando camera_id -> source."""
        source = self._resolve_source_from_camera_id(camera_id)
        if source is None:
            return False

        with self.lock:
            processor = self.camera_processors.get(source)
            thread = self.camera_threads.get(source)
            if processor:
                processor.stop()
            if thread and thread.is_alive():
                thread.join(timeout=2)
            # Mantém estruturas para possível reinício rápido
        return True
