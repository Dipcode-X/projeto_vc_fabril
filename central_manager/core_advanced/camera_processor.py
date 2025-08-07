import cv2
import numpy as np
from .visualization import Visualizer
from .detector import YOLODetector
from .state_manager_advanced_layer_01 import SimpleStateManager
from .simple_logger import SimpleLogger
from queue import Queue
import time
import os

# Cores do legacy (BGR format para OpenCV)
CORES_LEGACY = {
    'roi': (255, 0, 255),      # Rosa/Magenta para ROI
    'divisor': (0, 255, 255),  # Amarelo para divisor  
    'item': (0, 255, 0),       # Verde para itens
    'text': (255, 255, 255),   # Branco para texto
    'status': (0, 255, 255),   # Ciano para status
    'alert': (0, 0, 255),      # Vermelho para alertas
}

def filtrar_itens_na_roi(itens, caixas):
    """Filtra itens que estão dentro da ROI (caixa) principal."""
    if not caixas or not itens:
        return []
    
    itens_na_roi = []
    roi_coords, _ = caixas[0] # Pega a primeira ROI encontrada
    roi_x1, roi_y1, roi_x2, roi_y2 = roi_coords
    
    for item_coords, item_conf in itens:
        item_center_x = (item_coords[0] + item_coords[2]) // 2
        item_center_y = (item_coords[1] + item_coords[3]) // 2
        
        if (roi_x1 <= item_center_x <= roi_x2 and 
            roi_y1 <= item_center_y <= roi_y2):
            itens_na_roi.append((item_coords, item_conf))
            
    return itens_na_roi

class CameraProcessor:
    """Processa o feed de uma câmera, aplicando detecção e gerenciamento de estado."""
    def __init__(self, output_queue: Queue, camera_source=0, conf_roi=0.5, conf_item=0.4, conf_divisor=0.25):
        self.camera_source = camera_source
        self.output_queue = output_queue
        self.running = False
        self.should_stop = False
        self.reconnection_attempts = 0
        self.was_ever_connected = False
        self.disconnection_logged = False  # Flag para evitar spam de desconexão
        self.logger = SimpleLogger(f"Camera-{camera_source}")
        self.visualizer = Visualizer(CORES_LEGACY)
        self.detector = YOLODetector(confianca_roi=conf_roi, confianca_item=conf_item, confianca_divisor=conf_divisor)
        self.state_manager = SimpleStateManager()
        self.cap = None
        self.width = 0
        self.height = 0
        self.paused = False
        self.detection_enabled = True
        # --- Informações do Produto ---
        self.product_id = 1 # Placeholder
        self.product_name = "Produto Padrão" # Placeholder

    def stop(self):
        """Sinaliza para a thread de processamento parar."""
        self.should_stop = True
        self.running = False

    def get_status(self):
        """Retorna o estado atual do processador da câmera."""
        sm_status = self.state_manager.get_status()
        return {
            "id": self.camera_source,
            "source": str(self.camera_source), # Garante que seja string para JSON
            "running": self.running,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "status_message": sm_status.get('estado', 'N/A')
        }

    def initialize(self):
        """Inicializa a captura da câmera e configura a resolução."""
        self.cap = cv2.VideoCapture(self.camera_source)
        if not self.cap.isOpened():
            self.logger.warning(f"Não foi possível abrir a câmera {self.camera_source}")
            return False
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.logger.info(f"Câmera {self.camera_source} aberta com sucesso ({self.width}x{self.height})")
        return True

    def process_frame(self, frame):
        """Processa um frame da câmera."""
        frame = cv2.flip(frame, 1)
        
        caixas, itens, divisores, itens_na_roi = [], [], [], []
        if self.detection_enabled:
            caixas, itens, divisores = self.detector.detectar_objetos(frame)
            itens_na_roi = filtrar_itens_na_roi(itens, caixas)
            roi_presente = len(caixas) > 0
            self.state_manager.atualizar_estado(roi_presente, itens_na_roi, divisores)
        
        status_info = self.state_manager.get_status()
        
        # Adiciona de volta a exibição dos controles na tela
        self.visualizer.desenhar_controles(frame, self.height)

        contadores_yolo = {
            'detection_enabled': self.detection_enabled,
            'roi': len(caixas),
            'itens_roi': len(itens_na_roi),
            'divisores': len(divisores)
        }
        self.visualizer.desenhar_painel_status(frame, status_info, self.width, self.height, contadores_yolo)
        self.visualizer.desenhar_deteccoes(frame, caixas, itens_na_roi, divisores)

        if self.paused:
            self.visualizer.desenhar_overlay_pausa(frame, self.width, self.height)
        
        # Em vez de mostrar, coloca o frame na fila
        try:
            self.output_queue.put_nowait({'frame': frame, 'status': self.state_manager.get_status()})
        except Exception: # Normalmente queue.Full
            # Se a fila estiver cheia, descarta o frame para não travar o processamento.
            pass

    def run(self):
        """O loop principal de processamento da câmera."""
        self.cap = cv2.VideoCapture(self.camera_source)
        if not self.cap.isOpened():
            self.logger.warning(f"Câmera {self.camera_source} não encontrada - aguardando conexão...")
            self.running = False
        else:
            self.logger.info(f"Câmera {self.camera_source} aberta com sucesso ({int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))})")
            self.running = True
            self.was_ever_connected = True

        # Loop principal - continua rodando mesmo se a câmera se desconectar
        while not self.should_stop:
            if self.running and not self.paused:
                # Câmera está conectada - processa frames normalmente
                ret, frame = self.cap.read()
                if not ret:
                    if self.was_ever_connected:
                        self.logger.error(f"Câmera {self.camera_source} desconectada - aguardando reconexão...")
                    self.running = False
                    self.cap.release()
                    self.reconnection_attempts = 0
                    continue
                
                # Processa o frame normalmente
                self.process_frame(frame)
                
            elif not self.running:
                # Câmera desconectada - tenta reconectar periodicamente
                self.reconnection_attempts += 1
                
                # Log apenas na primeira tentativa para evitar spam
                if self.reconnection_attempts == 1:
                    if self.was_ever_connected:
                        self.logger.error(f"Câmera {self.camera_source} desconectada - aguardando reconexão...")
                    # Para câmeras nunca conectadas, já foi logado no início
                
                # Suprime temporariamente os logs do OpenCV para evitar spam
                cv2.setLogLevel(0)  # Silencia OpenCV
                self.cap = cv2.VideoCapture(self.camera_source)
                cv2.setLogLevel(1)  # Restaura logs do OpenCV
                
                if self.cap.isOpened():
                    self.logger.info(f"Câmera {self.camera_source} reconectada com sucesso!")
                    self.running = True
                    self.was_ever_connected = True
                    self.reconnection_attempts = 0
                    self.disconnection_logged = False
                else:
                    time.sleep(15)  # Aguarda 15 segundos antes de tentar novamente
                    
            else:
                # Câmera pausada
                time.sleep(0.1)

        # Cleanup ao sair
        if self.cap:
            self.cap.release()
        self.logger.info(f"Thread da câmera {self.camera_source} finalizada")

    def release(self):
        """Libera a câmera."""
        if self.cap:
            self.cap.release()
        self.logger.info(f"Câmera {self.camera_source} liberada.")
