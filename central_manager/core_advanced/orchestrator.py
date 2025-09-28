# central_manager/core_advanced/orchestrator.py
import threading
from queue import Queue
from typing import Dict, List, Any

from .camera_processor import CameraProcessor
from .simple_logger import SimpleLogger
from ..database.connection import DatabaseManager


class Orchestrator:
    """Gerencia múltiplos processadores de câmera em threads separadas."""

    def __init__(self):
        self.logger = SimpleLogger("Orchestrator")
        self.is_running = False
        self.camera_processors: Dict[Any, CameraProcessor] = {}
        self.camera_threads: Dict[Any, threading.Thread] = {}
        self.lock = threading.Lock()
        self.db_manager = DatabaseManager()
        # Estrutura compatível com os endpoints (/cameras/*) que esperam {'processor','queue'}
        self.camera_data: Dict[Any, Dict[str, Any]] = {}

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
                    self.logger.info(
                        f"  -> Encontrada Câmera USB: ID {cam.id}, Índice {cam.device_index} ({cam.nome})"
                    )

                # Para câmeras IP, a fonte é a URL (a ser construída ou extraída)
                elif cam.ip_address:
                    # TODO: Construir a URL RTSP completa a partir dos campos do DB
                    # Por enquanto, vamos assumir que ip_address já é a URL
                    camera_sources.append(cam.ip_address)
                    self.logger.info(
                        f"  -> Encontrada Câmera IP: ID {cam.id}, URL {cam.ip_address} ({cam.nome})"
                    )

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

        output_queue = Queue(maxsize=2)  # Fila pequena para evitar latência
        processor = CameraProcessor(output_queue=output_queue, camera_source=camera_source)

        self.camera_processors[camera_source] = processor
        # Mapa utilizado pelos endpoints para status/stream
        self.camera_data[camera_source] = {"processor": processor, "queue": output_queue}

    def start(self):
        """Inicia o orquestrador e o processamento das câmeras."""
        self.is_running = True
        cameras_to_process = self._discover_cameras()
        for source in cameras_to_process:
            self.add_camera(source)
            self._start_processor_thread(source)
        self.logger.info("Orquestrador iniciado.")

    def _start_processor_thread(self, camera_source):
        """Inicia uma thread de processamento para uma câmera específica."""
        thread = threading.Thread(
            target=self.camera_processors[camera_source].run, daemon=True
        )
        self.camera_threads[camera_source] = thread
        thread.start()
        self.logger.info(f"Thread da câmera {camera_source} iniciada.")

    def start_processor(self, camera_source):
        """Inicia o processamento para uma câmera específica.

        - Se a câmera não existir ainda, cria e inicia.
        - Se a thread anterior terminou, recria o processor/queue para estado limpo.
        """
        with self.lock:
            thread = self.camera_threads.get(camera_source)
            if (
                camera_source not in self.camera_processors
                or thread is None
                or not thread.is_alive()
            ):
                # (Re)cria processor e fila para garantir estado limpo
                output_queue = Queue(maxsize=2)
                processor = CameraProcessor(
                    output_queue=output_queue, camera_source=camera_source
                )
                self.camera_processors[camera_source] = processor
                self.camera_data[camera_source] = {
                    "processor": processor,
                    "queue": output_queue,
                }
                self._start_processor_thread(camera_source)
                return True

            # Já existe e está rodando
            self.logger.info(f"Câmera {camera_source} já está com thread ativa.")
            return True

    def stop_processor(self, camera_source):
        """Para o processamento de uma câmera específica e aguarda a thread finalizar."""
        with self.lock:
            processor = self.camera_processors.get(camera_source)
            thread = self.camera_threads.get(camera_source)
            if not processor:
                self.logger.warning(
                    f"Solicitado stop para câmera inexistente: {camera_source}"
                )
                return False
            # Sinaliza parada
            processor.stop()
            if thread and thread.is_alive():
                thread.join()
            # Mantém estruturas para permitir consulta de status posterior (running=False)
            self.logger.info(f"Câmera {camera_source} parada.")
            return True

    def rescan_cameras(self) -> Dict[str, Any]:
        """Para, limpa e redescobre as câmeras a partir do banco de dados."""
        self.logger.info("Iniciando rebusca manual de câmeras...")

        # 1. Parar processadores existentes
        self.stop_all_processors()

        # 2. Limpar listas
        with self.lock:
            self.camera_processors.clear()
            self.camera_threads.clear()
            self.camera_data.clear()
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
            "camera_list": cameras_to_process,
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
        for source in list(self.camera_processors.keys()):
            self.stop_processor(source)

    def get_camera_data(self, camera_source):
        """Retorna os dados (processador e fila) de uma câmera específica."""
        return self.camera_data.get(camera_source)

    def get_all_cameras_summary(self):
        """Retorna uma lista de resumos do estado de todas as câmeras."""
        return [data["processor"].get_status() for data in self.camera_data.values()]