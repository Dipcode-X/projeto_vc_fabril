import os
from ultralytics import YOLO

# Configurações dos modelos (movido do legacy)
MODELOS = {
    'item_detector': '_legacy_prototype/modelos_producao/item_detector.pt',
    'roi_detector': '_legacy_prototype/modelos_producao/roi_detector.pt'
}

class YOLODetector:
    """Classe para encapsular a lógica de detecção YOLO."""
    def __init__(self, confianca_roi=0.5, confianca_item=0.4, confianca_divisor=0.25):
        print("🧠 Carregando modelos YOLO...")
        
        # Validação de caminhos
        if not os.path.exists(MODELOS['roi_detector']):
            print(f"❌ Erro: Modelo ROI não encontrado em {MODELOS['roi_detector']}")
            raise FileNotFoundError(f"Modelo ROI não encontrado em {MODELOS['roi_detector']}")
        if not os.path.exists(MODELOS['item_detector']):
            print(f"❌ Erro: Modelo de item/divisor não encontrado em {MODELOS['item_detector']}")
            raise FileNotFoundError(f"Modelo de item/divisor não encontrado em {MODELOS['item_detector']}")
            
        self.modelo_roi = YOLO(MODELOS['roi_detector'])
        self.modelo_itens = YOLO(MODELOS['item_detector'])
        print("✅ Modelos YOLO carregados com sucesso!")
        
        self.confianca_roi = confianca_roi
        self.confianca_item = confianca_item
        self.confianca_divisor = confianca_divisor
        
        print(f"🔹 Confiança ROI/Itens: {self.confianca_roi}/{self.confianca_item}")
        print(f"🔹 Confiança Divisores: {self.confianca_divisor}")

    def detectar_objetos(self, frame):
        """Detecta ROI, itens e divisores no frame."""
        try:
            # Detectar ROI
            resultados_roi = self.modelo_roi(frame, verbose=False)
            caixas = []
            for r in resultados_roi:
                for box in r.boxes:
                    if box.conf >= self.confianca_roi:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        caixas.append(((x1, y1, x2, y2), float(box.conf)))
            
            # Detectar Itens e Divisores
            resultados_itens = self.modelo_itens(frame, verbose=False)
            itens = []
            divisores = []
            for r in resultados_itens:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf)
                    cls = int(box.cls[0])
                    
                    if cls == 0 and conf >= self.confianca_item: # Classe 0: item
                        itens.append(((x1, y1, x2, y2), conf))
                    elif cls == 1 and conf >= self.confianca_divisor: # Classe 1: divisor
                        divisores.append(((x1, y1, x2, y2), conf))
            
            return caixas, itens, divisores
        except Exception as e:
            print(f"❌ Erro na detecção: {e}")
            return [], [], []