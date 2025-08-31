import time
from collections import deque
import math
import traceback

from .config import STATE_CONFIG, MQTT_CONFIG
from .simple_logger import SimpleLogger
from .alert_manager import AlertManager




class SimpleStateManager:
    """StateManager com lógica avançada do legacy (memória espacial + detecção de saltos)"""
    
    def __init__(self, alert_manager=None, camera_id=None):
        self.logger = SimpleLogger("STATE_MANAGER")
        self.config = STATE_CONFIG # Usa a configuração do próprio módulo

        self.alert_manager = alert_manager
        if not self.alert_manager:
            self.logger.warning("AlertManager não foi fornecido. Alertas estarão desativados.")
        self.camera_id = camera_id

        # Estados
        self.ESTADOS = self.config['estados']
        self.PERFIL_CAIXA = self.config['perfil_caixa']
        
        # Estado atual
        self.status_sistema = self.ESTADOS['AGUARDANDO_CAIXA']
        self.camada_atual = 1
        self.contagem_estabilizada = 0
        self.contagens_por_camada = {1: 0, 2: 0}
        
        # Buffers de estabilização
        self.buffer_roi = deque(maxlen=self.config['tamanho_buffer_estabilizacao'])
        self.buffer_contagem_itens = deque(maxlen=self.config['tamanho_buffer_estabilizacao'])
        self.buffer_divisor_presente = deque(maxlen=self.config['tamanho_buffer_estabilizacao'])
        
        # MEMÓRIA ESPACIAL (do legacy)
        self.usar_memoria_espacial = True
        self.posicoes_itens_por_camada = {}  # {camada: [(x1,y1,x2,y2), ...]}
        
        # DETECÇÃO DE SALTOS (do legacy)
        self.salto_suspeito_detectado = False
        self.tempo_inicio_salto_suspeito = None
        self.itens_salto_suspeito = []
        self.contagem_anterior_camada_2 = 0
        self.tempo_ultima_contagem_camada_2 = None
        
        # Controle de tempo
        self.caixa_ausente_desde = None
        self.ultimo_alerta_tempo = None
        self.ultimo_alerta_tipo = None
        self.primeira_deteccao = True
        self.ultima_contagem_valida = 0 # Guarda a última contagem antes de perder a ROI
        
        # Controle do LED ESP32
        self.led_ativo = False  # Estado atual do LED
        
        # Lógica de camada estabelecida
        self.camada_2_estabelecida = False
        self.tempo_ultimo_divisor_ausente = None
        self.tempo_ultima_contagem_baixa = None
        
        # NOVA FUNCIONALIDADE: Rastreamento do divisor para validação de saltos
        self.tempo_ultimo_divisor_estavel = None  # Quando divisor ficou estável
        self.tempo_ultima_perda_divisor = None    # Quando divisor foi perdido
        self.divisor_estava_presente_frame_anterior = False  # Estado anterior do divisor
        
        self.logger.info("StateManager AVANÇADO inicializado com memória espacial, detecção de saltos e validação por divisor")

    def _enviar_comando_led(self, comando):
        """Envia comando para o LED via MQTT (on/off)."""
        if not self.alert_manager:
            self.logger.warning("AlertManager não inicializado. Comando LED não pode ser enviado.")
            return

        try:
            topics_cfg = MQTT_CONFIG.get('topics', {})
            default_topic = topics_cfg.get('led_command_default', 'guizo/00')
            led_map = topics_cfg.get('led_topic_map', {})
            cam_key = str(self.camera_id) if self.camera_id is not None else None
            topic = led_map.get(cam_key, default_topic)
            self.alert_manager.send_alert(topic, comando)
            self.logger.info(f"Comando LED enviado (topic='{topic}'): {comando}")
            
            # Atualizar estado interno do LED
            if comando == "on":
                self.led_ativo = True
            elif comando == "off":
                self.led_ativo = False
                # Publicar ROI OFF + evento de restauração quando LED é desligado
                self._publish_roi_state("OFF", reason="led_off")
                self._publish_roi_event("roi_restored", {"reason": "led_off"})
                
        except Exception as e:
            self.logger.error(f"Falha ao enviar comando LED: {e}")

    def _enviar_alerta_caixa_incompleta(self, contagem_no_momento_da_perda):
        """Envia um alerta para uma caixa removida com contagem de itens incompleta."""
        itens_faltantes = self.PERFIL_CAIXA['itens_por_camada'] - contagem_no_momento_da_perda
        mensagem = (
            f"Caixa removida INCOMPLETA na camada {self.camada_atual}. "
            f"Contagem: {contagem_no_momento_da_perda}/{self.PERFIL_CAIXA['itens_por_camada']}. "
            f"Faltaram {itens_faltantes} itens."
        )
        self.logger.error(f"🚨 ALERTA: {mensagem}")
        
        # Acender LED no ESP32
        self._enviar_comando_led("on")
        
        # Publicar ROI ON + evento de remoção incorreta
        self._publish_roi_state("ON", reason="roi_lost_incomplete", extra={
            "missing": itens_faltantes,
            "expected": self.PERFIL_CAIXA['itens_por_camada'],
            "count_at_loss": contagem_no_momento_da_perda,
        })
        self._publish_roi_event("roi_incorrect_removal", {
            "missing": itens_faltantes,
            "expected": self.PERFIL_CAIXA['itens_por_camada'],
            "count_at_loss": contagem_no_momento_da_perda,
        })

    def _desligar_led_se_ativo(self):
        """Desliga o LED se estiver ativo."""
        if self.led_ativo:
            self._enviar_comando_led("off")
            self.logger.info("LED desligado - ROI retornou ou caixa completa")

    def _enviar_alerta_caixa_incompleta_original(self):
        """Envia um alerta de caixa removida incompleta via MQTT."""
        if not self.alert_manager:
            self.logger.warning("AlertManager não inicializado. Alerta não pode ser enviado.")
            return

        try:
            payload = {
                "tipo_alerta": "caixa_incompleta",
                "mensagem": f"Caixa removida com {self.contagem_estabilizada} de {self.PERFIL_CAIXA['itens_por_camada']} itens.",
                "camada_atual": self.camada_atual,
                "contagem_atual": self.contagem_estabilizada
            }
            self.alert_manager.publish_alert(payload)
            self.logger.info(f"Alerta de caixa incompleta enviado: {payload['mensagem']}")
        except Exception as e:
            self.logger.error(f"Falha ao enviar alerta de caixa incompleta: {e}")
    
    def _obter_valores_estabilizados(self):
        """Obtém valores estabilizados dos buffers"""
        if len(self.buffer_roi) < self.config['tamanho_buffer_estabilizacao']:
            return False, 0, False
        
        # ROI estável se maioria dos frames tem ROI
        roi_estavel = sum(self.buffer_roi) >= (len(self.buffer_roi) * 0.6)
        
        # Contagem estabilizada (mediana)
        contagens = sorted(self.buffer_contagem_itens)
        contagem_estabilizada = contagens[len(contagens) // 2]
        
        # Divisor estável se maioria dos frames tem divisor
        divisor_estavel = sum(self.buffer_divisor_presente) >= (len(self.buffer_divisor_presente) * 0.6)
        
        return roi_estavel, contagem_estabilizada, divisor_estavel
    
    def _verificar_itens_novos(self, itens_atuais):
        """
        MEMÓRIA ESPACIAL: Verifica quais itens são realmente novos comparando com camadas anteriores
        Resolve o problema de falsos positivos quando divisor é removido
        """
        if not self.usar_memoria_espacial or not self.posicoes_itens_por_camada:
            return itens_atuais  # Se não tem memória, considera todos novos
        
        itens_novos = []
        
        for item_atual in itens_atuais:
            x1_atual, y1_atual, x2_atual, y2_atual = item_atual[0]  # Coordenadas
            centro_atual = ((x1_atual + x2_atual) / 2, (y1_atual + y2_atual) / 2)
            
            eh_novo = True
            
            # Comparar com itens de todas as camadas anteriores
            for camada_anterior, itens_anteriores in self.posicoes_itens_por_camada.items():
                if not eh_novo:
                    break
                    
                for item_anterior in itens_anteriores:
                    x1_ant, y1_ant, x2_ant, y2_ant = item_anterior[0]  # Coordenadas
                    centro_anterior = ((x1_ant + x2_ant) / 2, (y1_ant + y2_ant) / 2)
                    
                    # Calcular distância euclidiana entre os centros
                    distancia = math.sqrt(
                        (centro_atual[0] - centro_anterior[0]) ** 2 + 
                        (centro_atual[1] - centro_anterior[1]) ** 2
                    )
                    
                    if distancia < self.config['distancia_minima_item_novo']:
                        # Item muito próximo de um item anterior, não é novo
                        eh_novo = False
                        self.logger.debug(f"Item descartado (distância {distancia:.1f}px da camada {camada_anterior})")
                        break
                
                if not eh_novo:
                    break
            
            if eh_novo:
                itens_novos.append(item_atual)
                self.logger.debug(f"Item novo confirmado: centro {centro_atual}")
        
        self.logger.info(f"Memória espacial: {len(itens_novos)}/{len(itens_atuais)} itens são novos")
        return itens_novos
    
    def _atualizar_status_divisor(self, divisor_presente):
        """
        Atualiza o rastreamento do status do divisor para validação de saltos.
        Deve ser chamado a cada frame para manter histórico preciso.
        """
        tempo_atual = time.time()
        
        # Detectar mudança no status do divisor
        if divisor_presente != self.divisor_estava_presente_frame_anterior:
            if divisor_presente:
                # Divisor apareceu - resetar tempo de estabilidade
                self.tempo_ultimo_divisor_estavel = tempo_atual
                self.tempo_ultima_perda_divisor = None
                self.logger.debug("Divisor detectado - iniciando contagem de estabilidade")
            else:
                # Divisor desapareceu - marcar tempo de perda
                self.tempo_ultima_perda_divisor = tempo_atual
                self.tempo_ultimo_divisor_estavel = None
                self.logger.debug("Divisor perdido - marcando instabilidade")
        
        # Atualizar estado anterior
        self.divisor_estava_presente_frame_anterior = divisor_presente
    
    def _validar_salto_por_divisor(self, contagem_atual, salto, tempo_decorrido):
        """
        NOVA FUNCIONALIDADE: Valida salto baseado no status do divisor.
        
        Lógica:
        - Se divisor estável há tempo suficiente: ACEITAR salto (itens reais)
        - Se divisor perdido recentemente: REJEITAR salto (falso positivo)
        - Se situação ambígua: usar validação tradicional
        
        Returns:
            'aceitar': Salto deve ser aceito
            'rejeitar': Salto deve ser rejeitado  
            'validar': Usar validação tradicional (memória espacial)
        """
        try:
            self.logger.debug("🔍 INÍCIO _validar_salto_por_divisor")
            
            if not self.config.get('usar_validacao_divisor_salto', False):
                self.logger.debug("🔍 Validação por divisor desabilitada")
                return 'validar'  # Funcionalidade desabilitada
            
            tempo_atual = time.time()
            self.logger.debug(f"🔍 tempo_atual obtido: {tempo_atual}")
            
            tempo_estavel_minimo = self.config.get('tempo_divisor_estavel_minimo', 3.0)
            tempo_max_instabilidade = self.config.get('tempo_maximo_instabilidade_divisor', 2.0)
            
            # Verificações de segurança
            if tempo_atual is None or not isinstance(tempo_atual, (int, float)):
                self.logger.warning("Erro ao obter tempo atual - usando validação tradicional")
                return 'validar'
            
            self.logger.debug(f"🔍 Verificando cenários - divisor_presente: {self.divisor_estava_presente_frame_anterior}")
            
            # CENÁRIO 1: Divisor presente e estável há tempo suficiente
            if (self.divisor_estava_presente_frame_anterior and 
                self.tempo_ultimo_divisor_estavel is not None):
                
                self.logger.debug(f"🔍 CENÁRIO 1 - Calculando tempo estável...")
                tempo_estavel = tempo_atual - self.tempo_ultimo_divisor_estavel
                self.logger.debug(f"🔍 tempo_estavel calculado: {tempo_estavel}")
                
                if tempo_estavel >= tempo_estavel_minimo:
                    self.logger.info(f"✅ SALTO ACEITO por divisor estável: {self.contagem_anterior_camada_2} → {contagem_atual} "
                                   f"(divisor estável há {tempo_estavel:.1f}s)")
                    return 'aceitar'
                else:
                    self.logger.debug(f"Divisor ainda não estável o suficiente: {tempo_estavel:.1f}s < {tempo_estavel_minimo}s")
                    return 'validar'
            
            # CENÁRIO 2: Divisor perdido recentemente (suspeito de falso positivo)
            elif (not self.divisor_estava_presente_frame_anterior and 
                  self.tempo_ultima_perda_divisor is not None):
                
                self.logger.debug(f"🔍 CENÁRIO 2 - Calculando tempo desde perda...")
                tempo_desde_perda = tempo_atual - self.tempo_ultima_perda_divisor
                self.logger.debug(f"🔍 tempo_desde_perda calculado: {tempo_desde_perda}")
                
                if tempo_desde_perda <= tempo_max_instabilidade:
                    self.logger.warning(f"❌ SALTO REJEITADO por divisor instável: {self.contagem_anterior_camada_2} → {contagem_atual} "
                                      f"(divisor perdido há {tempo_desde_perda:.1f}s)")
                    return 'rejeitar'
                else:
                    self.logger.debug(f"Divisor ausente há muito tempo: {tempo_desde_perda:.1f}s > {tempo_max_instabilidade}s")
                    return 'validar'
            
            # CENÁRIO 3: Situação ambígua - usar validação tradicional
            else:
                self.logger.debug("🔍 CENÁRIO 3 - Status do divisor ambíguo - usando validação tradicional")
                return 'validar'
                
        except Exception as e:
            self.logger.error(f"❌ ERRO DETALHADO na validação por divisor:")
            self.logger.error(f"   Exceção: {e}")
            self.logger.error(f"   Tipo: {type(e).__name__}")
            self.logger.error(f"   Stack trace: {traceback.format_exc()}")
            return 'validar'  # Fallback para validação tradicional
    
    def _processar_logica_camada_2(self, divisor_estavel, contagem_atual):
        """
        Lógica avançada para controle da camada 2:
        - Até 4 itens: Exige divisor presente
        - 5+ itens: Considera camada estabelecida, divisor pode ser ocultado
        - < 5 itens após estabelecida: Volta a exigir divisor com carência
        """
        tempo_atual = time.time()
        
        # VERIFICAR MODO LIVRE PRIMEIRO - se ativo, ignorar todas as validações
        if hasattr(self, 'camada_2_modo_livre') and self.camada_2_modo_livre:
            self.logger.debug(f"🚫 MODO LIVRE: Ignorando lógica de divisor - {contagem_atual} itens")
            return True
        
        # Se a camada 2 ainda não foi estabelecida (< 5 itens)
        if not hasattr(self, 'camada_2_estabelecida'):
            self.camada_2_estabelecida = False
            
        # Verificar se deve desabilitar checagens permanentemente aos 8 itens
        if not hasattr(self, 'camada_2_modo_livre'):
            self.camada_2_modo_livre = False
            
        if not self.camada_2_modo_livre and contagem_atual >= 8:
            self.camada_2_modo_livre = True
            self.logger.info(f"🚫 MODO LIVRE ATIVADO: {contagem_atual} itens - Divisor e saltos DESABILITADOS até reiniciar ciclo")
            return True
        
        # Lógica normal até 8 itens (divisor obrigatório até 5 itens)
        if not self.camada_2_estabelecida:
            # Verificar se atingiu o mínimo para estabelecer (5 itens)
            if contagem_atual >= self.config.get('ITENS_MINIMOS_CAMADA_2_ESTABELECIDA', 5):
                self.camada_2_estabelecida = True
                self.logger.info(f"🎯 CAMADA 2 ESTABELECIDA com {contagem_atual} itens")
                return True
            
            # Ainda não estabelecida, exigir divisor
            if not divisor_estavel:
                if not hasattr(self, 'tempo_ultimo_divisor_ausente'):
                    self.tempo_ultimo_divisor_ausente = tempo_atual
                
                tempo_carencia = tempo_atual - self.tempo_ultimo_divisor_ausente
                carencia_maxima = self.config.get('TEMPO_CARENCIA_DIVISOR_AUSENTE', 3.0)
                
                if tempo_carencia > carencia_maxima:
                    self.logger.warning(f"❌ Divisor ausente há {tempo_carencia:.1f}s na camada 2. Voltando para camada 1")
                    self._voltar_para_camada_1()
                    return False
            else:
                # Divisor presente, reset carência
                self.tempo_ultimo_divisor_ausente = None
        
        return True
    
    def _voltar_para_camada_1(self):
        """Volta para a camada 1 quando há problemas na camada 2"""
        self.logger.warning("🔄 VOLTANDO PARA CAMADA 1")
        self.camada_atual = 1
        self.camada_2_estabelecida = False
        self.camada_2_modo_livre = False  # Reset do modo livre
        self.tempo_ultimo_divisor_ausente = None
        self.tempo_ultima_contagem_baixa = None
        
        # Reset controles de salto
        self.contagem_anterior_camada_2 = 0
        self.tempo_ultima_contagem_camada_2 = None
        self.salto_suspeito_detectado = False
        self.tempo_inicio_salto_suspeito = None
        self.itens_salto_suspeito = []
        
        # Reset buffers
        self.buffer_contagem_itens.clear()
        
        # Reset controle de falso positivo
        self.falso_positivo_detectado = False
        self.tempo_ultimo_falso_positivo = None
        self.contagem_rejeitada_anterior = 0
        
        # Transitar para aguardar divisor
        self._transitar_para(self.ESTADOS['AGUARDANDO_DIVISOR'], "Problemas na camada 2")
    
    def _processar_deteccao_saltos(self, contagem_atual, itens_na_roi):
        """
        DETECÇÃO DE SALTOS: Detecta mudanças bruscas na contagem (falsos positivos)
        Lógica híbrida como no legacy original
        """
        tempo_atual = time.time()
        
        # PROCESSAMENTO DE SALTO SUSPEITO EM VALIDAÇÃO
        if self.salto_suspeito_detectado:
            tempo_validacao = tempo_atual - self.tempo_inicio_salto_suspeito
            
            # Se o tempo de validação expirou, tomar uma decisão
            if tempo_validacao > self.config['tempo_carencia_salto']:
                # Usar memória espacial para validar
                novos_itens_percent = self._validar_memoria_espacial(self.itens_salto_suspeito, itens_na_roi)
                
                if novos_itens_percent >= self.config['percentual_novos_itens_minimo']:
                    # Salto confirmado como válido
                    self.logger.info(f"✅ SALTO CONFIRMADO: {self.contagem_anterior_camada_2} → {contagem_atual} ({novos_itens_percent:.0%} de itens novos)")
                    self.contagem_anterior_camada_2 = contagem_atual
                else:
                    # Salto considerado falso positivo
                    self.logger.warning(f"❌ FALSO POSITIVO CONFIRMADO: {self.contagem_anterior_camada_2} → {contagem_atual} ({novos_itens_percent:.0%} de itens novos)")
                    self._voltar_para_aguardar_divisor()
                
                self._reset_controles_salto()
            
            return False # Manter processamento pausado durante validação
        
        # Só aplicar para camada 2
        if self.camada_atual != 2:
            return True
        
        # Se camada 2 está em modo livre, ignorar saltos completamente
        if hasattr(self, 'camada_2_modo_livre') and self.camada_2_modo_livre:
            self.logger.debug(f"🚫 Modo livre ativo - IGNORANDO saltos ({len(itens_na_roi)} itens)")
            return True
        
        # Primeira contagem da camada 2, inicializar controles
        if self.tempo_ultima_contagem_camada_2 is None:
            self.contagem_anterior_camada_2 = contagem_atual
            self.tempo_ultima_contagem_camada_2 = tempo_atual
            return True
        
        # Calcular salto e tempo decorrido
        salto = contagem_atual - self.contagem_anterior_camada_2
        tempo_decorrido = tempo_atual - self.tempo_ultima_contagem_camada_2
        
        # DETECÇÃO DE SALTO SUSPEITO (usando configuração corrigida)
        if salto >= self.config['salto_suspeito_minimo'] and tempo_decorrido < self.config['tempo_maximo_salto']:
            # NOVA FUNCIONALIDADE: Primeiro tentar validação por divisor
            decisao_divisor = self._validar_salto_por_divisor(contagem_atual, salto, tempo_decorrido)
            
            if decisao_divisor == 'aceitar':
                # Salto aceito imediatamente por divisor estável
                self.contagem_anterior_camada_2 = contagem_atual
                self.tempo_ultima_contagem_camada_2 = tempo_atual
                return True
            elif decisao_divisor == 'rejeitar':
                # Salto rejeitado imediatamente por divisor instável
                self._voltar_para_aguardar_divisor()
                return False
            else:
                # decisao_divisor == 'validar' - usar lógica tradicional
                self.logger.warning(f"🚨 SALTO SUSPEITO: {self.contagem_anterior_camada_2} → {contagem_atual} em {tempo_decorrido:.1f}s")
                self.salto_suspeito_detectado = True
                self.tempo_inicio_salto_suspeito = tempo_atual
                self.itens_salto_suspeito = itens_na_roi.copy()
                return False  # Pausar processamento
        
        # Se não houve salto, atualizar contagem e tempo
        self.contagem_anterior_camada_2 = contagem_atual
        self.tempo_ultima_contagem_camada_2 = tempo_atual
        return True
    
    def _transitar_para(self, novo_estado, motivo=""):
        """Transição de estado com log"""
        if self.status_sistema != novo_estado:
            self.logger.info(f"TRANSIÇÃO: {self.status_sistema} → {novo_estado} - {motivo}")
            self.status_sistema = novo_estado
    
    def _pode_alertar(self, tipo_alerta, intervalo_minimo=3.0):
        """Controle de debounce para alertas"""
        tempo_atual = time.time()
        
        if (self.ultimo_alerta_tipo == tipo_alerta and 
            self.ultimo_alerta_tempo and 
            (tempo_atual - self.ultimo_alerta_tempo) < intervalo_minimo):
            return False
        
        self.ultimo_alerta_tempo = tempo_atual
        self.ultimo_alerta_tipo = tipo_alerta
        return True
    
    def _voltar_para_aguardar_divisor(self):
        """Volta para aguardar divisor quando salto é rejeitado (lógica do legacy)"""
        self.logger.info("🔄 Retornando para aguardar divisor devido a salto inválido")
        
        # Reset completo para camada 1
        self.camada_atual = 1
        self.camada_2_estabelecida = False
        self.tempo_ultimo_divisor_ausente = None
        self.tempo_ultima_contagem_baixa = None
        
        # Reset controles de salto
        self.contagem_anterior_camada_2 = 0
        self.tempo_ultima_contagem_camada_2 = None
        self.salto_suspeito_detectado = False
        self.tempo_inicio_salto_suspeito = None
        self.itens_salto_suspeito = []
        
        # Reset buffers
        self.buffer_contagem_itens.clear()
        
        # Reset controle de falso positivo
        self.falso_positivo_detectado = False
        self.tempo_ultimo_falso_positivo = None
        self.contagem_rejeitada_anterior = 0
        
        # Transitar para aguardar divisor
        self._transitar_para(self.ESTADOS['AGUARDANDO_DIVISOR'], "Salto rejeitado - aguardando divisor")
    
    def _reset_controles_salto(self):
        """Reset dos controles de detecção de saltos (do legacy)"""
        self.salto_suspeito_detectado = False
        self.tempo_inicio_salto_suspeito = None
        self.itens_salto_suspeito = []
    
    def _mqtt_topics(self):
        """Resolve tópicos por câmera para ROI state/event."""
        base_state = MQTT_CONFIG.get('topics', {}).get('roi_state_base')
        base_event = MQTT_CONFIG.get('topics', {}).get('roi_event_base')
        cam = self.camera_id if self.camera_id is not None else "unknown"
        state_topic = base_state.format(camera_id=cam) if base_state else None
        event_topic = base_event.format(camera_id=cam) if base_event else None
        return state_topic, event_topic

    def _publish_roi_state(self, state, reason="", extra=None):
        if not self.alert_manager:
            return
        state_topic, _ = self._mqtt_topics()
        if not state_topic:
            return
        payload = {
            "camera_id": self.camera_id,
            "state": state,
            "ts": int(time.time()),
            "reason": reason,
            "layer": self.camada_atual,
            "count": self.ultima_contagem_valida if state == "ON" else self.contagem_estabilizada,
        }
        if extra:
            payload.update(extra)
        try:
            # Retida para refletir o último estado conhecido
            self.alert_manager.publish_json(state_topic, payload, qos=1, retain=True)
        except Exception as e:
            self.logger.error(f"Falha ao publicar ROI state: {e}")

    def _publish_roi_event(self, event, details=None):
        if not self.alert_manager:
            return
        _, event_topic = self._mqtt_topics()
        if not event_topic:
            return
        payload = {
            "camera_id": self.camera_id,
            "event": event,
            "ts": int(time.time()),
            "layer": self.camada_atual,
            "count": self.contagem_estabilizada,
        }
        if details:
            payload.update(details)
        try:
            self.alert_manager.publish_json(event_topic, payload, qos=1, retain=False)
        except Exception as e:
            self.logger.error(f"Falha ao publicar ROI event: {e}")
    
    def atualizar_estado(self, roi_presente, itens_detectados, divisores_detectados):
        """Atualiza estado com lógica avançada (memória espacial + detecção de saltos)"""
        tempo_atual = time.time()
        
        # Atualizar buffers
        self.buffer_roi.append(1 if roi_presente else 0)
        self.buffer_contagem_itens.append(len(itens_detectados))
        self.buffer_divisor_presente.append(1 if divisores_detectados else 0)
        
        # Obter valores estabilizados
        roi_estavel, contagem_atual, divisor_estavel = self._obter_valores_estabilizados()
        
        # NOVA FUNCIONALIDADE: Atualizar rastreamento do divisor para validação de saltos
        self._atualizar_status_divisor(divisor_estavel)
        if not roi_estavel and len(self.buffer_roi) >= self.config['tamanho_buffer_estabilizacao']:
            roi_estavel, contagem_atual, divisor_estavel = self._obter_valores_estabilizados()
        
        # VERIFICAR MODO LIVRE DA CAMADA 2 (com validação temporal)
        if self.camada_atual == 2:
            if not hasattr(self, 'camada_2_modo_livre'):
                self.camada_2_modo_livre = False
            if not hasattr(self, 'modo_livre_habilitado'):
                self.modo_livre_habilitado = False
            
            # Lógica de validação temporal: 4+ itens por 3 segundos
            if contagem_atual >= 4:
                if not hasattr(self, 'tempo_inicio_validacao_modo_livre') or self.tempo_inicio_validacao_modo_livre is None:
                    self.tempo_inicio_validacao_modo_livre = tempo_atual
                    self.logger.debug(f"🕰️ Iniciando validação temporal para modo livre: {contagem_atual} itens")
                
                tempo_validacao = tempo_atual - self.tempo_inicio_validacao_modo_livre
                
                # Habilitar modo livre após 3 segundos com 4+ itens
                if tempo_validacao >= 3.0 and not self.modo_livre_habilitado:
                    self.modo_livre_habilitado = True
                    self.logger.info(f"✅ MODO LIVRE HABILITADO: {tempo_validacao:.1f}s com {contagem_atual} itens - Condição dos 8 itens liberada")
                
                # Ativar modo livre aos 8 itens (apenas se habilitado)
                if self.modo_livre_habilitado and not self.camada_2_modo_livre and contagem_atual >= 8:
                    self.camada_2_modo_livre = True
                    self.logger.info(f"🚫 MODO LIVRE ATIVADO: {contagem_atual} itens - Divisor e saltos DESABILITADOS até reiniciar ciclo")
            
            else:
                # Reset timer se cai abaixo de 4 itens
                if hasattr(self, 'tempo_inicio_validacao_modo_livre') and self.tempo_inicio_validacao_modo_livre is not None:
                    self.logger.debug(f"🔄 Reset validação temporal: {contagem_atual} itens < 4")
                self.tempo_inicio_validacao_modo_livre = None
                self.modo_livre_habilitado = False
        
        # Salvar a última contagem válida enquanto a caixa está presente e sendo contada
        if roi_estavel and self.status_sistema == self.ESTADOS['CONTANDO_ITENS']:
            if contagem_atual > 0:
                self.ultima_contagem_valida = contagem_atual

        # APLICAR DETECÇÃO DE SALTOS na camada 2
        if self.camada_atual == 2:
            if not self._processar_deteccao_saltos(contagem_atual, itens_detectados):
                # Salto suspeito detectado, pausar processamento
                return
        
        self.contagem_estabilizada = contagem_atual
        
        # Máquina de estados com lógica avançada
        estado_atual = self.status_sistema
        
        if estado_atual == self.ESTADOS['AGUARDANDO_CAIXA']:
            if roi_estavel:
                self._transitar_para(self.ESTADOS['CONTANDO_ITENS'], "ROI detectada")
        
# ...
        elif estado_atual == self.ESTADOS['CONTANDO_ITENS']:
            if not roi_estavel:
                # Condição para caixa removida incompleta - USA A ÚLTIMA CONTAGEM VÁLIDA
                if self.ultima_contagem_valida > 0 and self.ultima_contagem_valida < self.PERFIL_CAIXA['itens_por_camada']:
                    if self._pode_alertar("caixa_incompleta", 3.0):
                        self._enviar_alerta_caixa_incompleta(self.ultima_contagem_valida)
                        self.logger.info("Caixa incompleta removida. Resetando o sistema.")
                        self._resetar_sistema() # CORREÇÃO: Resetar completamente
                        return
                
                # Se a contagem for 0 ou o alerta não puder ser enviado, apenas transita
                self._transitar_para(self.ESTADOS['AGUARDANDO_CAIXA'], "ROI perdida")
                self._resetar_contagem_para_novo_ciclo() # Limpa a última contagem válida
                return
            
            # Verificar se camada está completa
            if self.contagem_estabilizada >= self.PERFIL_CAIXA['itens_por_camada']:
                # VERIFICAR SE CAMADA 2 ESTÁ EM MODO LIVRE (8+ itens)
                if (self.camada_atual == 2 and hasattr(self, 'camada_2_modo_livre') and self.camada_2_modo_livre):
                    self.logger.info(f"🚫 MODO LIVRE: Ignorando validação de memória espacial - {self.contagem_estabilizada} itens")
                # APLICAR VALIDAÇÃO COM MEMÓRIA ESPACIAL (apenas se não estiver em modo livre)
                elif self.usar_memoria_espacial and self.camada_atual > 1:
                    itens_novos = self._verificar_itens_novos(itens_detectados)
                    percentual_novos = len(itens_novos) / len(itens_detectados) if itens_detectados else 0
                    
                    if percentual_novos < self.config['percentual_itens_novos_minimo']:
                        # FALSO POSITIVO DETECTADO - voltar para aguardar divisor
                        self.falso_positivo_detectado = True
                        self.tempo_ultimo_falso_positivo = tempo_atual
                        self.contagem_rejeitada_anterior = self.contagem_estabilizada
                        
                        self.logger.warning(f"❌ Camada {self.camada_atual} REJEITADA: apenas {percentual_novos:.1%} itens novos (falso positivo)")
                        self._voltar_para_aguardar_divisor()  # VOLTA PARA CAMADA 1
                        return  # Não avançar, aguardar itens realmente novos
                
                # Camada válida - armazenar na memória espacial
                if self.usar_memoria_espacial:
                    self.posicoes_itens_por_camada[self.camada_atual] = itens_detectados.copy()
                    self.logger.info(f"📍 Posições da camada {self.camada_atual} armazenadas: {len(itens_detectados)} itens")
                
                self.contagens_por_camada[self.camada_atual] = self.contagem_estabilizada
                
                if self.camada_atual >= self.PERFIL_CAIXA['total_camadas']:
                    # Caixa completa
                    total_itens = sum(self.contagens_por_camada.values())
                    self.logger.info(f"🎯 CAIXA COMPLETA! Total: {total_itens} itens")
                    self._desligar_led_se_ativo()  # Desligar LED se ativo
                    self._transitar_para(self.ESTADOS['CAIXA_COMPLETA'], "Todas as camadas completas")
                else:
                    # Aguardar divisor para próxima camada
                    self.logger.info(f"🎯 CAMADA {self.camada_atual} COMPLETA: {self.contagem_estabilizada}/{self.PERFIL_CAIXA['itens_por_camada']} itens")
                    self._transitar_para(self.ESTADOS['AGUARDANDO_DIVISOR'], f"Camada {self.camada_atual} completa")
        
        elif estado_atual == self.ESTADOS['AGUARDANDO_DIVISOR']:
            if not roi_estavel:
                if self._pode_alertar("caixa_pos_camada_completa", 5.0):
                    self.logger.error(f"🚨 ALERTA: Caixa removida após completar camada {self.camada_atual}!")
                self._transitar_para(self.ESTADOS['AGUARDANDO_CAIXA'], "ROI perdida aguardando divisor")
                return
            
            if divisor_estavel and self.contagem_estabilizada == 0:
                # Divisor cobrindo itens, avançar para próxima camada
                self.camada_atual += 1
                self.logger.info(f"➡️ Avançando para camada {self.camada_atual}")
                self._transitar_para(self.ESTADOS['CONTANDO_ITENS'], f"Iniciando camada {self.camada_atual}")
            
            # Lógica de camada estabelecida
            if self.camada_atual == 2:
                if not self._processar_logica_camada_2(divisor_estavel, self.contagem_estabilizada):
                    return
        
        elif estado_atual == self.ESTADOS['CAIXA_COMPLETA']:
            if not roi_estavel:
                self.logger.info("✅ Caixa completa removida. Reiniciando ciclo")
                self._resetar_sistema()
        
        elif estado_atual == self.ESTADOS['CAIXA_AUSENTE']:
            if roi_estavel:
                self.logger.info("✅ Caixa reapareceu")
                self._desligar_led_se_ativo()  # Desligar LED quando ROI retorna
                self._transitar_para(self.ESTADOS['CONTANDO_ITENS'], "ROI reapareceu")
                self.caixa_ausente_desde = None
    
    def _resetar_contagem_para_novo_ciclo(self):
        """Reseta a contagem para um novo ciclo sem resetar o sistema inteiro."""
        self.ultima_contagem_valida = 0
        self.logger.debug("Última contagem válida resetada para novo ciclo.")

    def _resetar_sistema(self):
        """Reset completo do sistema"""
        self._desligar_led_se_ativo()  # Garante desligamento do LED no reset
        self.logger.info("🔄 Sistema resetado")
        self._transitar_para(self.ESTADOS['AGUARDANDO_CAIXA'], "Reset do sistema")
        self.camada_atual = 1
        self.contagens_por_camada = {1: 0, 2: 0}
        self.contagem_estabilizada = 0
        self.ultima_contagem_valida = 0 # Resetar também no reset geral
        self.led_ativo = False  # Reset do estado do LED
        self.buffer_roi.clear()
        self.buffer_contagem_itens.clear()
        self.buffer_divisor_presente.clear()
        
        # Reset da memória espacial e detecção de saltos
        self.posicoes_itens_por_camada.clear()
        self.salto_suspeito_detectado = False
        
        # Reset do modo livre da camada 2
        self.camada_2_estabelecida = False
        self.camada_2_modo_livre = False
        self.modo_livre_habilitado = False
        self.tempo_inicio_validacao_modo_livre = None
        self.tempo_ultimo_divisor_ausente = None
        self.tempo_ultima_contagem_baixa = None
        self.tempo_inicio_salto_suspeito = None
        self.itens_salto_suspeito = []
        self.contagem_anterior_camada_2 = 0
        self.tempo_ultima_contagem_camada_2 = None
        self.primeira_deteccao = True
        
        # Reset da lógica de camada estabelecida
        self.camada_2_estabelecida = False
        self.tempo_ultimo_divisor_ausente = None
        self.tempo_ultima_contagem_baixa = None
        
        # Reset do rastreamento do divisor
        self.tempo_ultimo_divisor_estavel = None
        self.tempo_ultima_perda_divisor = None
        self.divisor_estava_presente_frame_anterior = False

        # Reset das novas variáveis de controle temporal do modo livre
        self.tempo_inicio_validacao_modo_livre = None
        self.modo_livre_habilitado = False

    def get_status(self):
        """Retorna status atual para interface"""
        total_itens = sum(self.contagens_por_camada.values()) + (self.contagem_estabilizada if self.status_sistema == self.ESTADOS['CONTANDO_ITENS'] else 0)
        
        # Adicionar informações de debug da lógica avançada
        debug_info = ""
        if self.salto_suspeito_detectado:
            debug_info = " (VALIDANDO SALTO)"
        elif self.usar_memoria_espacial and self.posicoes_itens_por_camada:
            debug_info = f" (MEM: {len(self.posicoes_itens_por_camada)} camadas)"
        
        return {
            'estado': self.status_sistema + debug_info,
            'camada_atual': self.camada_atual,
            'contagem_atual': self.contagem_estabilizada,
            'meta_camada': self.PERFIL_CAIXA['itens_por_camada'],
            'total_itens': total_itens,
            'camadas': self.contagens_por_camada.copy()
        }