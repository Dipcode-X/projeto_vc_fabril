"""
SIAC Orchestrator - Gerenciador Central de Câmeras e Produtos
Substitui o papel do main.py legacy, gerenciando múltiplas instâncias de processamento
"""

class SiacOrchestrator:
    """
    Orquestrador central que gerencia múltiplas câmeras e produtos dinamicamente.
    Cada câmera roda em sua própria thread via SiacProcessor.
    """
    
    def __init__(self):
        # TODO: Implementar inicialização
        pass
    
    def start_camera_processor(self, camera_id: str, product_config: dict):
        """Inicia processamento para uma câmera específica"""
        # TODO: Implementar
        pass
    
    def stop_camera_processor(self, camera_id: str):
        """Para processamento de uma câmera específica"""
        # TODO: Implementar
        pass
    
    def switch_product(self, camera_id: str, new_product_config: dict):
        """Troca produto/modelo YOLO de uma câmera em runtime"""
        # TODO: Implementar
        pass
    
    def get_camera_status(self, camera_id: str):
        """Retorna status atual de uma câmera"""
        # TODO: Implementar
        pass
    
    def get_all_cameras_status(self):
        """Retorna status de todas as câmeras ativas"""
        # TODO: Implementar
        pass
