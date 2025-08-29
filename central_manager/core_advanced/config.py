# Arquivo de configuração para o StateManager

STATE_CONFIG = {
    'estados': {
        'AGUARDANDO_CAIXA': 'AGUARDANDO_CAIXA',
        'CONTANDO_ITENS': 'CONTANDO_ITENS',
        'VERIFICANDO_CAMADA': 'VERIFICANDO_CAMADA',
        'AGUARDANDO_DIVISOR': 'AGUARDANDO_DIVISOR',
        'ALERTA_DIVISOR_AUSENTE': 'ALERTA_DIVISOR_AUSENTE',
        'CAIXA_COMPLETA': 'CAIXA_COMPLETA',
        'CAIXA_AUSENTE': 'CAIXA_AUSENTE'
    },
    'perfil_caixa': {
        'itens_por_camada': 12,
        'total_camadas': 2,
        'itens_esperados': 12
    },
    'tamanho_buffer_estabilizacao': 5,
    'percentual_itens_novos_minimo': 0.7,  # CORRIGIDO: 70% como no legacy
    'distancia_minima_item_novo': 50,
    'tempo_limite_caixa_ausente': 30.0,
    'itens_minimos_camada_2_estabelecida': 5,
    'tempo_carencia_divisor_ausente': 3.0,
    'tempo_carencia_contagem_baixa': 2.0,
    'salto_suspeito_minimo': 3,  # CORRIGIDO: 3 como no legacy (não 5)
    'tempo_carencia_salto': 2.0,
    'tempo_maximo_salto': 2.0,  # ADICIONADO: do legacy
    'percentual_itens_novos_salto': 0.7,  # ADICIONADO: do legacy
    
    # NOVA FUNCIONALIDADE: Validação de salto baseada no status do divisor
    'tempo_divisor_estavel_minimo': 3.0,  # Tempo mínimo que divisor deve estar estável
    'tempo_maximo_instabilidade_divisor': 2.0,  # Tempo após perda do divisor considerado suspeito
    'usar_validacao_divisor_salto': True,  # Habilitar validação por divisor
}

MQTT_CONFIG = {
    'broker_ip': '10.1.4.12', # IP do broker MQTT (alinhado ao ESP32)
    'broker_port': 1883, # Porta do broker MQTT
    'client_id': 'siac_central_manager', # ID do cliente para conexão
    'topics': {
        'caixa_incompleta': 'siac/alertas/caixa_incompleta',
        'caixa_removida': 'siac/alertas/caixa_removida',
        'caixa_completa': 'siac/alertas/caixa_completa',
        'falso_positivo': 'siac/alertas/falso_positivo',
        'erro_sistema': 'siac/alertas/erro_sistema',
        'roi_state_base': 'siac/roi/{camera_id}/state',
        'roi_event_base': 'siac/roi/{camera_id}/event',
        'led_command_default': 'guizo/00',
        'led_topic_map': {
            '0': 'guizo/00',  # Mapeia camera_id "0" ao tópico do ESP32
        }
    }
}