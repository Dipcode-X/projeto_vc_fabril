"""
Teste EVOLUTIVO da Câmera - Agora com StateManagerAdvanced integrado
Evolução incremental: Câmera + YOLO + StateManager industrial
"""

print("🎥 Teste da Câmera + YOLO + StateManager")
print("=" * 45)

try:
    import cv2
    import numpy as np
    import os
    import sys
    import time
    from collections import deque
    import math
    from central_manager.core_advanced.visualization import Visualizer
    from central_manager.core_advanced.detector import YOLODetector
    from central_manager.core_advanced.state_manager_advanced_layer_01 import SimpleStateManager
    print("✅ Bibliotecas importadas com sucesso!")
except ImportError as e:
    print(f"❌ Erro ao importar: {e}")
    print("💡 Tente: pip install opencv-python numpy")
    input("Pressione Enter para sair...")
    exit()

# Configurações de confiança (do legacy)
CONFIDENCIA_LIMITE = 0.4
CONFIDENCIA_DIVISOR = 0.25  # Confiança mais baixa para divisores

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
    
    # Para cada ROI detectada
    for roi_coords, roi_conf in caixas:
        roi_x1, roi_y1, roi_x2, roi_y2 = roi_coords
        
        # Verificar quais itens estão dentro desta ROI
        for item_coords, item_conf in itens:
            item_x1, item_y1, item_x2, item_y2 = item_coords
            
            # Centro do item
            item_center_x = (item_x1 + item_x2) // 2
            item_center_y = (item_y1 + item_y2) // 2
            
            # Verificar se o centro do item está dentro da ROI
            if (roi_x1 <= item_center_x <= roi_x2 and 
                roi_y1 <= item_center_y <= roi_y2):
                itens_na_roi.append((item_coords, item_conf))
    
    return itens_na_roi

try:
    # Inicializar componentes
    visualizer = Visualizer(CORES_LEGACY)
    detector = YOLODetector(confianca_roi=0.5, confianca_item=CONFIDENCIA_LIMITE, confianca_divisor=CONFIDENCIA_DIVISOR)
    state_manager = SimpleStateManager() # A configuração agora é interna ao módulo
    
    # Abrir câmera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Não foi possível abrir a câmera")
        print("💡 Verifique se a câmera está conectada e não está sendo usada por outro programa")
        input("Pressione Enter para sair...")
        exit()
    
    print("✅ Câmera aberta com sucesso!")
    
    # Configurar resolução
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    # Obter informações da câmera
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"📊 Resolução: {width}x{height}")
    print(f"📊 FPS: {fps}")
    print()
    print("🎮 CONTROLES:")
    print("- ESC: Sair")
    print("- SPACE: Pausar/Continuar")
    print("- D: Toggle detecção YOLO")
    print("- R: Reset StateManager")
    print()
    print("🎯 SISTEMA INTEGRADO:")
    print("- Rosa: ROI (caixa)")
    print("- Verde: ITENS (numerados)")
    print("- Amarelo: DIVISORES")
    print("- Painel direito: Status do StateManager")
    print("=" * 45)
    
    paused = False
    detection_enabled = True
    
    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                print("❌ Erro ao capturar frame")
                break
            
            # Espelhar imagem para ficar mais natural
            frame = cv2.flip(frame, 1)
            
            # Detectar objetos se habilitado
            caixas = []
            itens = []
            divisores = []
            
            if detection_enabled:
                caixas, itens, divisores = detector.detectar_objetos(frame)
                itens_na_roi = filtrar_itens_na_roi(itens, caixas)
                
                # Atualizar StateManager
                roi_presente = len(caixas) > 0
                state_manager.atualizar_estado(roi_presente, itens_na_roi, divisores)
            
            # Obter status do StateManager
            status_info = state_manager.get_status()
            
            # Desenhar informações de ajuda e status no frame USANDO O VISUALIZER
            visualizer.desenhar_controles(frame, height)
            contadores_yolo = {
                'detection_enabled': detection_enabled,
                'roi': len(caixas),
                'itens_roi': len(itens_na_roi),
                'divisores': len(divisores)
            }
            visualizer.desenhar_painel_status(frame, status_info, width, height, contadores_yolo)

            # Desenhar detecções USANDO O VISUALIZER
            if detection_enabled:
                visualizer.desenhar_deteccoes(frame, caixas, itens_na_roi, divisores) # CORRIGIDO
            
            # Se pausado, mostrar overlay USANDO O VISUALIZER
            if paused:
                visualizer.desenhar_overlay_pausa(frame, width, height)
        
        # Mostrar frame
        cv2.imshow('SIAC - Teste Completo: YOLO + StateManager', frame)
        
        # Processar teclas
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC
            print("🛑 Saindo...")
            break
        elif key == ord(' '):  # SPACE
            paused = not paused
            status = "PAUSADO" if paused else "RODANDO"
            print(f"⏸️ Status: {status}")
        elif key == ord('d') or key == ord('D'):  # D
            detection_enabled = not detection_enabled
            status = "LIGADA" if detection_enabled else "DESLIGADA"
            print(f"🤖 Detecção YOLO: {status}")
        elif key == ord('r') or key == ord('R'):  # R
            state_manager._resetar_sistema()
            print("🔄 StateManager resetado manualmente")

except Exception as e:
    print(f"❌ Erro inesperado: {e}")
    
finally:
    try:
        cap.release()
        cv2.destroyAllWindows()
        print("✅ Câmera liberada")
    except:
        pass
    
    print("🎥 Teste finalizado")
    input("Pressione Enter para sair...")
