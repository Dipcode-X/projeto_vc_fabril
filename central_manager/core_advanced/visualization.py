import cv2

# Cores do legacy (BGR format para OpenCV)
CORES_LEGACY = {
    'roi': (255, 0, 255),      # Rosa/Magenta para ROI
    'divisor': (0, 255, 255),  # Amarelo para divisor
    'item': (0, 255, 0),       # Verde para itens
    'text': (255, 255, 255),   # Branco para texto
    'status': (0, 255, 255),   # Amarelo para status (originalmente ciano no comentário)
    'alert': (0, 0, 255),      # Vermelho para alertas
}

class Visualizer:
    """Encapsula toda a lógica de desenho para manter o código principal limpo."""

    def __init__(self, colors=None):
        """Inicializa o visualizador com um conjunto de cores."""
        self.colors = colors if colors else CORES_LEGACY

    def desenhar_deteccoes(self, frame, caixas, itens, divisores):
        """Desenha as detecções no frame (ROI, itens, divisores)."""
        # Desenhar ROI
        for coords, conf in caixas:
            x1, y1, x2, y2 = coords
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.colors['roi'], 3)
            cv2.putText(frame, "ROI", (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors['roi'], 2)

        # Desenhar Itens
        for coords, conf in itens:
            x1, y1, x2, y2 = coords
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.colors['item'], 2)

        # Desenhar Divisores
        for coords, conf in divisores:
            x1, y1, x2, y2 = coords
            cv2.rectangle(frame, (x1, y1), (x2, y2), self.colors['divisor'], 2)
            cv2.putText(frame, "DIV", (x1, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, self.colors['divisor'], 1)

    def desenhar_painel_status(self, frame, status, width, height, contadores_yolo):
        """Desenha o painel de status completo com informações do sistema."""
        panel_width = 250
        panel_height = 220
        panel_x = width - panel_width - 10
        panel_y = 10

        # Fundo semi-transparente
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, panel_y),
                      (panel_x + panel_width, panel_y + panel_height),
                      (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Borda
        cv2.rectangle(frame, (panel_x, panel_y),
                      (panel_x + panel_width, panel_y + panel_height),
                      self.colors['text'], 2)

        # Textos
        y_offset = panel_y + 20
        line_height = 16

        # Status YOLO
        yolo_status = "YOLO: ON" if contadores_yolo.get('detection_enabled', False) else "YOLO: OFF"
        cv2.putText(frame, yolo_status, (panel_x + 10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.colors['status'], 1)

        # Contadores YOLO
        y_offset += line_height + 2
        cv2.putText(frame, f"ROI: {contadores_yolo.get('roi', 0)}", (panel_x + 10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.colors['roi'], 1)
        y_offset += line_height
        cv2.putText(frame, f"ITENS: {contadores_yolo.get('itens_roi', 0)}", (panel_x + 10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.colors['item'], 1)
        y_offset += line_height
        cv2.putText(frame, f"DIVISORES: {contadores_yolo.get('divisores', 0)}", (panel_x + 10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.colors['divisor'], 1)

        # Separador
        y_offset += line_height + 5
        cv2.line(frame, (panel_x + 10, y_offset), (panel_x + panel_width - 10, y_offset),
                 self.colors['text'], 1)

        # Estado do StateManager
        y_offset += 15
        estado_display = status.get('estado', 'N/A').replace('_', ' ')
        cv2.putText(frame, "ESTADO:", (panel_x + 10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.colors['text'], 1)
        y_offset += 15
        cv2.putText(frame, estado_display, (panel_x + 10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.colors['status'], 1)

        # Informações da contagem
        y_offset += line_height + 2
        cv2.putText(frame, f"CAMADA: {status.get('camada_atual', 'N/A')}", (panel_x + 10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.colors['text'], 1)
        y_offset += line_height
        cv2.putText(frame, f"CONTAGEM: {status.get('contagem_atual', 0)}/{status.get('meta_camada', 0)}", (panel_x + 10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.colors['item'], 1)
        y_offset += line_height
        cv2.putText(frame, f"TOTAL: {status.get('total_itens', 0)}", (panel_x + 10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, self.colors['text'], 1)

        # Progresso por camada
        y_offset += line_height + 5
        cv2.putText(frame, "CAMADAS:", (panel_x + 10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.3, self.colors['text'], 1)
        for camada, contagem in status.get('camadas', {}).items():
            y_offset += 12
            cv2.putText(frame, f"  {camada}: {contagem}", (panel_x + 15, y_offset),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, self.colors['text'], 1)

    def desenhar_overlay_pausa(self, frame, width, height):
        """Desenha a mensagem 'PAUSADO' no centro da tela."""
        texto = "PAUSADO"
        (text_width, text_height), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 1, 3)
        text_x = (width - text_width) // 2
        text_y = (height + text_height) // 2
        cv2.putText(frame, texto, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, self.colors['alert'], 3)

    def desenhar_controles(self, frame, height):
        """Desenha o texto de ajuda para os controles do teclado."""
        y_offset = height - 70
        font_scale = 0.4
        line_height = 15
        cv2.putText(frame, "Esc: Sair", (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.colors['text'], 1)
        cv2.putText(frame, "Space: Pausar/Continuar", (10, y_offset + line_height), cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.colors['text'], 1)
        cv2.putText(frame, "D: Toggle YOLO", (10, y_offset + 2 * line_height), cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.colors['text'], 1)
        cv2.putText(frame, "R: Reset", (10, y_offset + 3 * line_height), cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.colors['text'], 1)