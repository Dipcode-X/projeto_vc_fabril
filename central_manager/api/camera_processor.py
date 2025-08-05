"""
SIAC Camera Processor - Processamento Isolado por Câmera
Encapsula o pipeline de processamento legacy para cada câmera/produto
"""

import threading
from typing import Dict, Any

class SiacProcessor:
    """
    Processador isolado que encapsula a lógica legacy para uma câmera específica.
    Roda em thread própria para evitar interferência entre câmeras.
    """
    
    def __init__(self, camera_id: str, product_config: Dict[str, Any]):
        self.camera_id = camera_id
        self.product_config = product_config
        self.is_running = False
        self.thread = None
        
        # TODO: Inicializar detector, state_manager, visualizer
        # baseado no product_config (core_simple ou core_advanced)
    
    def start(self):
        """Inicia o processamento da câmera em thread separada"""
        # TODO: Implementar
        pass
    
    def stop(self):
        """Para o processamento da câmera"""
        # TODO: Implementar
        pass
    
    def update_product_config(self, new_config: Dict[str, Any]):
        """Atualiza configuração do produto em runtime"""
        # TODO: Implementar
        pass
    
    def get_current_status(self):
        """Retorna status atual do processamento"""
        # TODO: Implementar
        pass
    
    def _processing_loop(self):
        """Loop principal de processamento (equivalente ao main.py legacy)"""
        # TODO: Implementar lógica do main.py legacy
        # - Captura de frames
        # - Detecção YOLO
        # - Atualização do StateManager
        # - Visualização
        pass
