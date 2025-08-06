import threading
from queue import Queue
from typing import Dict, Any

from .camera_processor import CameraProcessor

class Orchestrator:
    """Gerencia múltiplos processadores de câmera em threads separadas."""

    def __init__(self):
        self.processors: Dict[Any, Dict[str, Any]] = {}
        self.threads: Dict[Any, threading.Thread] = {}
        self.running = False

    def add_camera(self, camera_source):
        """Adiciona uma nova câmera para ser gerenciada."""
        if camera_source in self.processors:
            print(f"Aviso: Câmera {camera_source} já existe.")
            return

        output_queue = Queue(maxsize=2)  # Fila pequena para evitar latência
        processor = CameraProcessor(output_queue=output_queue, camera_source=camera_source)
        
        self.processors[camera_source] = {
            'processor': processor,
            'queue': output_queue
        }

    def start(self):
        """Inicia todas as threads de processamento de câmera."""
        self.running = True
        for source, data in self.processors.items():
            thread = threading.Thread(target=data['processor'].run, daemon=True)
            self.threads[source] = thread
            thread.start()
            print(f"Thread da câmera {source} iniciada.")

    def stop(self):
        """Para todos os processadores e aguarda as threads finalizarem."""
        print("Parando todos os processadores...")
        self.running = False
        for data in self.processors.values():
            data['processor'].stop()
        
        for source, thread in self.threads.items():
            thread.join()
            print(f"Thread da câmera {source} finalizada.")

    def get_camera_data(self, camera_source):
        """Retorna os dados (processador e fila) de uma câmera específica."""
        return self.processors.get(camera_source)
