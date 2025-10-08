"""
StateManager Simples - Para produtos de 1 camada
Versão simplificada para produtos de camada única, compatível com a API do avançado.
"""

import time
from collections import deque
from ..core_advanced.simple_logger import SimpleLogger


class StateManagerSimple:
    """
    StateManager simplificado para produtos de 1 camada.
    - Sem divisor obrigatório
    - Sem memória espacial / validação de saltos
    - Smoothing simples por mediana
    """

    def __init__(self, alert_manager=None, camera_id=None):
        self.logger = SimpleLogger("STATE_MANAGER_SIMPLE")
        self.alert_manager = alert_manager
        self.camera_id = camera_id

        # Estados mínimos
        self.ESTADOS = {
            'AGUARDANDO_CAIXA': 'AGUARDANDO_CAIXA',
            'CONTANDO_ITENS': 'CONTANDO_ITENS',
            'CAIXA_COMPLETA': 'CAIXA_COMPLETA',
            'CAIXA_AUSENTE': 'CAIXA_AUSENTE',
        }

        # Configuração simples (mantém chaves usadas pelo orchestrator)
        self.config = {
            'tamanho_buffer_estabilizacao': 5,
            'usar_validacao_divisor_salto': False,  # ignorado no modo simples, mas presente para compatibilidade
        }

        # Perfil de caixa (1 camada por padrão; orquestrador pode sobrescrever)
        self.PERFIL_CAIXA = {
            'itens_por_camada': 12,
            'total_camadas': 1,
            'itens_esperados': 12,
        }

        # Estado atual
        self.status_sistema = self.ESTADOS['AGUARDANDO_CAIXA']
        self.camada_atual = 1
        self.contagem_estabilizada = 0
        self.contagens_por_camada = {1: 0}

        # Buffers de estabilização
        n = self.config['tamanho_buffer_estabilizacao']
        self.buffer_roi = deque(maxlen=n)
        self.buffer_contagem_itens = deque(maxlen=n)

        self.logger.info("StateManager SIMPLE inicializado (1 camada)")

    def _mediana(self, arr):
        if not arr:
            return 0
        s = sorted(arr)
        return s[len(s) // 2]

    def atualizar_estado(self, roi_presente, itens_detectados, divisores_detectados):
        """
        Atualiza o estado simples:
        - roi_presente: bool
        - itens_detectados: lista de (bbox, conf) já filtrados na ROI
        - divisores_detectados: ignorado no modo simples
        """
        try:
            # Atualiza buffers
            self.buffer_roi.append(1 if roi_presente else 0)
            self.buffer_contagem_itens.append(len(itens_detectados) if itens_detectados else 0)

            # ROI estável por maioria simples (>= 60%) quando houver amostras suficientes
            roi_estavel = False
            if len(self.buffer_roi) >= 1:
                roi_estavel = sum(self.buffer_roi) >= (len(self.buffer_roi) * 0.6)

            # Smoothing por mediana
            self.contagem_estabilizada = int(self._mediana(list(self.buffer_contagem_itens)))
            self.contagens_por_camada[1] = self.contagem_estabilizada

            meta = int(self.PERFIL_CAIXA.get('itens_por_camada', 12) or 12)

            if not roi_estavel:
                self.status_sistema = self.ESTADOS['AGUARDANDO_CAIXA']
            else:
                if self.contagem_estabilizada >= meta:
                    self.status_sistema = self.ESTADOS['CAIXA_COMPLETA']
                else:
                    self.status_sistema = self.ESTADOS['CONTANDO_ITENS']
        except Exception as e:
            self.logger.error(f"Erro em atualizar_estado (simple): {e}")

    def get_status(self):
        """Retorna status atual para interface (compatível com o avançado)."""
        return {
            'estado': f"{self.status_sistema} (SIMPLE)",
            'camada_atual': self.camada_atual,
            'contagem_atual': self.contagem_estabilizada,
            'meta_camada': int(self.PERFIL_CAIXA.get('itens_por_camada', 12) or 12),
            'total_itens': self.contagem_estabilizada,
            'camadas': {1: self.contagem_estabilizada},
        }
