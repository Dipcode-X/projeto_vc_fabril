import os
import threading
from ultralytics import YOLO

# --- Path Correction ---
# Build paths relative to this file's location to avoid FileNotFoundError
DETECTOR_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(os.path.dirname(DETECTOR_DIR), 'models')

# Configurações dos modelos com caminhos corrigidos e robustos
MODELOS = {
    'item_detector': os.path.join(MODELS_DIR, 'item_detector.pt'),
    'roi_detector': os.path.join(MODELS_DIR, 'roi_detector.pt')
}

class YOLODetector:
    """Classe para encapsular a lógica de detecção YOLO."""
    def __init__(self, confianca_roi=0.5, confianca_item=0.4, confianca_divisor=0.25):
        print("🧠 Carregando modelos YOLO...")
        
        # Lock para uso thread-safe (reload em runtime)
        self._lock = threading.RLock()
        
        # Caminhos vigentes
        self.roi_model_path = MODELOS['roi_detector']
        self.item_model_path = MODELOS['item_detector']
        
        # Validação de caminhos
        if not os.path.exists(self.roi_model_path):
            print(f"❌ Erro: Modelo ROI não encontrado em {self.roi_model_path}")
            raise FileNotFoundError(f"Modelo ROI não encontrado em {self.roi_model_path}")
        if not os.path.exists(self.item_model_path):
            print(f"❌ Erro: Modelo de item/divisor não encontrado em {self.item_model_path}")
            raise FileNotFoundError(f"Modelo de item/divisor não encontrado em {self.item_model_path}")
            
        # Carregamento inicial
        self.modelo_roi = YOLO(self.roi_model_path)
        self.modelo_itens = YOLO(self.item_model_path)
        print("✅ Modelos YOLO carregados com sucesso!")
        
        self.confianca_roi = confianca_roi
        self.confianca_item = confianca_item
        self.confianca_divisor = confianca_divisor
        
        print(f"🔹 Confiança ROI/Itens: {self.confianca_roi}/{self.confianca_item}")
        print(f"🔹 Confiança Divisores: {self.confianca_divisor}")

    def _resolve_model_path(self, name_or_path: str) -> str:
        if not name_or_path:
            return None
        # Se vier só o nome do arquivo, resolve em MODELS_DIR
        if not os.path.isabs(name_or_path):
            return os.path.join(MODELS_DIR, name_or_path)
        return name_or_path

    def reload_models(self, item_model_name: str | None = None, roi_model_name: str | None = None) -> dict:
        """
        Recarrega dinamicamente os modelos do detector.
        Aceita nome de arquivo (será resolvido contra MODELS_DIR) ou caminho absoluto.
        Retorna um resumo do que foi aplicado.
        """
        applied = {}
        with self._lock:
            if roi_model_name:
                new_roi_path = self._resolve_model_path(roi_model_name)
                if not os.path.exists(new_roi_path):
                    raise FileNotFoundError(f"Modelo ROI não encontrado: {new_roi_path}")
                self.modelo_roi = YOLO(new_roi_path)
                self.roi_model_path = new_roi_path
                applied['roi_model'] = os.path.basename(new_roi_path)
            if item_model_name:
                new_item_path = self._resolve_model_path(item_model_name)
                if not os.path.exists(new_item_path):
                    raise FileNotFoundError(f"Modelo de itens não encontrado: {new_item_path}")
                self.modelo_itens = YOLO(new_item_path)
                self.item_model_path = new_item_path
                applied['item_model'] = os.path.basename(new_item_path)
        if applied:
            print(f"🔄 Modelos recarregados: {applied}")
        return applied

    def apply_thresholds(self, confianca_roi: float | None = None, confianca_item: float | None = None, confianca_divisor: float | None = None) -> dict:
        """Atualiza limiares de confiança usados na detecção."""
        applied = {}
        with self._lock:
            if confianca_roi is not None:
                self.confianca_roi = float(confianca_roi)
                applied['confianca_roi'] = self.confianca_roi
            if confianca_item is not None:
                self.confianca_item = float(confianca_item)
                applied['confianca_item'] = self.confianca_item
            if confianca_divisor is not None:
                self.confianca_divisor = float(confianca_divisor)
                applied['confianca_divisor'] = self.confianca_divisor
        if applied:
            print(f"⚙️ Thresholds atualizados: {applied}")
        return applied

    def detectar_objetos(self, frame):
        """Detecta ROI, itens e divisores no frame."""
        try:
            # Captura referências thread-safe para evitar race com reload
            with self._lock:
                modelo_roi = self.modelo_roi
                modelo_itens = self.modelo_itens
                conf_roi = self.confianca_roi
                conf_item = self.confianca_item
                conf_div = self.confianca_divisor

            # Detectar ROI
            resultados_roi = modelo_roi(frame, verbose=False)
            caixas = []
            for r in resultados_roi:
                for box in r.boxes:
                    if box.conf >= conf_roi:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        caixas.append(((x1, y1, x2, y2), float(box.conf)))
            
            # Detectar Itens e Divisores
            resultados_itens = modelo_itens(frame, verbose=False)
            itens = []
            divisores = []
            for r in resultados_itens:
                for box in r.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf)
                    cls = int(box.cls[0])
                    
                    if cls == 0 and conf >= conf_item: # Classe 0: item
                        itens.append(((x1, y1, x2, y2), conf))
                    elif cls == 1 and conf >= conf_div: # Classe 1: divisor
                        divisores.append(((x1, y1, x2, y2), conf))
            
            return caixas, itens, divisores
        except Exception as e:
            print(f"❌ Erro na detecção: {e}")
            return [], [], []