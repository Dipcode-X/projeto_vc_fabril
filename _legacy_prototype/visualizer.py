import cv2
from config import CORES, FONTE, ESPESSURA_LINHA
from logger_config import get_siac_logger, SiacLogger

class Visualizer:
    """
    Encapsula toda a lógica de desenho na imagem (visualização).
    """
    def __init__(self):
        """
        Inicializa com as constantes de desenho importadas da configuração.
        """
        self.logger = get_siac_logger("VISUALIZER")
        self.cores = CORES
        self.fonte = FONTE
        self.espessura = ESPESSURA_LINHA
        
        self.logger.info("Visualizer inicializado com configurações de desenho")

    def desenhar_visualizacoes(self, frame, roi, itens, divisores, status_visual):
        """
        Desenha todos os elementos visuais no frame.

        Args:
            frame: A imagem onde os desenhos serão feitos.
            roi: As coordenadas da região de interesse (caixa).
            itens: Uma lista das coordenadas dos itens detectados.
            divisores: Uma lista das coordenadas dos divisores detectados.
            status_visual: Um dicionário com as informações de status do sistema.
        """
        try:
            # Extrai informações do dicionário de status
            status_texto = status_visual.get('status_texto', 'ERRO')
            contagem = status_visual.get('contagem', 0)
            camada_atual = status_visual.get('camada', 1)  # Extrai a camada atual

            self.logger.debug(f"Desenhando visualizações - ROI: {roi is not None}, Itens: {len(itens)}, Divisores: {len(divisores)}")

            # Desenha a ROI
            if roi:
                x1, y1, x2, y2 = roi
                cv2.rectangle(frame, (x1, y1), (x2, y2), self.cores['roi'], self.espessura)
                cv2.putText(frame, "Caixa", (x1, y1 - 10), self.fonte, 0.7, self.cores['roi'], self.espessura)

            # Desenha os itens
            for item in itens:
                x1, y1, x2, y2 = item
                cv2.rectangle(frame, (x1, y1), (x2, y2), self.cores['item_ok'], self.espessura)

            # Desenha os divisores
            for divisor in divisores:
                x1, y1, x2, y2 = divisor
                cv2.rectangle(frame, (x1, y1), (x2, y2), self.cores['divisor'], self.espessura)
                cv2.putText(frame, "Divisor", (x1, y1 - 10), self.fonte, 0.7, self.cores['divisor'], self.espessura)

            # Desenha as informações de status e contagem
            self.desenhar_info_tela(frame, contagem, status_texto, camada_atual)
            
        except Exception as e:
            SiacLogger.log_error_with_context(self.logger, e, "Desenho das visualizações")


    def desenhar_info_tela(self, frame, contagem, status_texto, camada_atual):
        """
        Desenha os textos de status e contagem no canto superior da tela.
        """
        try:
            # Desenhar informações principais
            cv2.putText(frame, f"Status: {status_texto} | Camada: {camada_atual}", (10, 30), self.fonte, 0.8, self.cores['texto_status'], self.espessura)
            cv2.putText(frame, f"Itens Contados: {contagem}", (10, 60), self.fonte, 0.8, self.cores['texto_contagem'], self.espessura)
            
            # Adicionar timestamp no canto inferior direito
            import time
            timestamp = time.strftime("%H:%M:%S")
            cv2.putText(frame, timestamp, (frame.shape[1] - 100, frame.shape[0] - 10), self.fonte, 0.5, self.cores['texto_status'], 1)
            
        except Exception as e:
            SiacLogger.log_error_with_context(self.logger, e, "Desenho das informações na tela")
