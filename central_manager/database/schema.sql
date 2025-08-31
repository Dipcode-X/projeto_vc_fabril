-- =====================================================
-- SIAC Industrial - Schema do Banco de Dados
-- Arquitetura Centralizada: 1 PC + Múltiplas Câmeras
-- =====================================================

-- Setores da fábrica (ex: Montagem, Embalagem, Expedição)
CREATE TABLE setores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Linhas de produção dentro de cada setor
CREATE TABLE linhas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setor_id INTEGER NOT NULL REFERENCES setores(id) ON DELETE CASCADE,
    nome VARCHAR(100) NOT NULL,
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(setor_id, nome)
);

-- Produtos/Perfis de caixa com configurações específicas
CREATE TABLE produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome VARCHAR(100) NOT NULL UNIQUE,
    descricao TEXT,
    itens_por_camada INTEGER DEFAULT 12,
    max_camadas INTEGER DEFAULT 2,
    
    -- Configurações de detecção
    confidence_threshold REAL DEFAULT 0.5,
    divisor_confidence REAL DEFAULT 0.7,
    divisor_low_confidence REAL DEFAULT 0.3,
    
    -- Configurações de contagem
    buffer_size_roi INTEGER DEFAULT 5,
    buffer_size_divisor INTEGER DEFAULT 3,
    frames_estabilizacao INTEGER DEFAULT 3,
    
    -- Memória espacial e validações
    distancia_minima_item INTEGER DEFAULT 50,
    percentual_itens_novos_minimo REAL DEFAULT 0.6,
    
    -- Carências e timeouts
    carencia_caixa_ausente REAL DEFAULT 2.0,
    carencia_divisor_ausente REAL DEFAULT 3.0,
    timeout_alerta_minimo REAL DEFAULT 5.0,
    
    -- Tolerâncias
    tolerancia_oclusao_camada2 INTEGER DEFAULT 2,
    limiar_salto_contagem INTEGER DEFAULT 3,
    tempo_validacao_salto REAL DEFAULT 2.0,
    
    -- Configurações extras em JSON
    config_json TEXT DEFAULT '{}',
    
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Câmeras conectadas ao PC central
CREATE TABLE cameras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    linha_id INTEGER NOT NULL REFERENCES linhas(id) ON DELETE CASCADE,
    produto_id INTEGER REFERENCES produtos(id) ON DELETE SET NULL,
    
    nome VARCHAR(100) NOT NULL,
    device_index INTEGER,           -- Índice da câmera USB (0, 1, 2...)
    ip_address VARCHAR(45),         -- IP se for câmera de rede
    porta INTEGER,                  -- Porta se for câmera de rede
    
    -- Configurações de vídeo
    resolucao_width INTEGER DEFAULT 1920,
    resolucao_height INTEGER DEFAULT 1080,
    fps INTEGER DEFAULT 30,
    
    -- Status e monitoramento
    status VARCHAR(20) DEFAULT 'offline', -- offline, online, error
    last_check TIMESTAMP,
    error_message TEXT,
    
    -- Configurações específicas da câmera
    config_json TEXT DEFAULT '{}',
    
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(linha_id),  -- Uma câmera por linha
    CHECK (device_index IS NOT NULL OR ip_address IS NOT NULL)
);

-- Dispositivos de alerta (ESP32, buzzers, LEDs, etc)
CREATE TABLE dispositivos_alerta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id INTEGER NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    
    tipo VARCHAR(50) NOT NULL,      -- "esp32", "buzzer", "led", "serial"
    nome VARCHAR(100) NOT NULL,
    
    -- Conexão
    endereco VARCHAR(100),          -- IP, porta serial, etc
    porta INTEGER,                  -- Porta TCP/UDP se aplicável
    baudrate INTEGER,               -- Baudrate se serial
    
    -- Configurações específicas
    config_json TEXT DEFAULT '{}',  -- Comandos, timeouts, etc
    
    -- Status
    status VARCHAR(20) DEFAULT 'offline',
    last_ping TIMESTAMP,
    error_message TEXT,
    
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dados de produção em tempo real
CREATE TABLE producao_dados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id INTEGER NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Estado atual da linha
    estado VARCHAR(50) NOT NULL,    -- AGUARDANDO_CAIXA, CONTANDO_ITENS, etc
    contagem_atual INTEGER DEFAULT 0,
    camada_atual INTEGER DEFAULT 1,
    caixas_completas INTEGER DEFAULT 0,
    
    -- Detecções do frame
    roi_detectada BOOLEAN DEFAULT FALSE,
    itens_detectados INTEGER DEFAULT 0,
    divisores_detectados INTEGER DEFAULT 0,
    
    -- Alertas e eventos
    alertas_json TEXT DEFAULT '[]', -- Lista de alertas gerados
    eventos_json TEXT DEFAULT '[]', -- Eventos importantes
    
    -- Métricas de performance
    fps_atual REAL,
    tempo_processamento REAL,       -- Tempo para processar o frame (ms)
    memoria_uso REAL,               -- Uso de memória (MB)
    
    -- Dados extras
    dados_json TEXT DEFAULT '{}'
);

-- Histórico de alertas para auditoria
CREATE TABLE alertas_historico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    camera_id INTEGER NOT NULL REFERENCES cameras(id) ON DELETE CASCADE,
    
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    tipo VARCHAR(50) NOT NULL,      -- "caixa_incompleta", "divisor_ausente", etc
    severidade VARCHAR(20) DEFAULT 'warning', -- info, warning, error, critical
    mensagem TEXT NOT NULL,
    
    -- Contexto do alerta
    estado_anterior VARCHAR(50),
    estado_atual VARCHAR(50),
    contagem_atual INTEGER,
    camada_atual INTEGER,
    
    -- Ação tomada
    acao_tomada VARCHAR(100),       -- "buzzer_acionado", "email_enviado", etc
    dispositivo_alerta_id INTEGER REFERENCES dispositivos_alerta(id),
    
    -- Resolução
    resolvido BOOLEAN DEFAULT FALSE,
    resolvido_em TIMESTAMP,
    resolvido_por VARCHAR(100),
    
    dados_json TEXT DEFAULT '{}'
);

-- Configurações globais do sistema
CREATE TABLE configuracoes_sistema (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chave VARCHAR(100) NOT NULL UNIQUE,
    valor TEXT,
    tipo VARCHAR(20) DEFAULT 'string', -- string, integer, real, boolean, json
    descricao TEXT,
    categoria VARCHAR(50),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- ÍNDICES PARA PERFORMANCE
-- =====================================================

-- Índices para consultas frequentes
CREATE INDEX idx_linhas_setor ON linhas(setor_id);
CREATE INDEX idx_cameras_linha ON cameras(linha_id);
CREATE INDEX idx_cameras_produto ON cameras(produto_id);
CREATE INDEX idx_dispositivos_camera ON dispositivos_alerta(camera_id);
CREATE INDEX idx_producao_camera ON producao_dados(camera_id);
CREATE INDEX idx_producao_timestamp ON producao_dados(timestamp);
CREATE INDEX idx_alertas_camera ON alertas_historico(camera_id);
CREATE INDEX idx_alertas_timestamp ON alertas_historico(timestamp);
CREATE INDEX idx_alertas_tipo ON alertas_historico(tipo);

-- =====================================================
-- TRIGGERS PARA UPDATED_AT
-- =====================================================

-- Trigger para atualizar updated_at automaticamente
CREATE TRIGGER update_setores_timestamp 
    AFTER UPDATE ON setores
    BEGIN
        UPDATE setores SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_linhas_timestamp 
    AFTER UPDATE ON linhas
    BEGIN
        UPDATE linhas SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_produtos_timestamp 
    AFTER UPDATE ON produtos
    BEGIN
        UPDATE produtos SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

CREATE TRIGGER update_cameras_timestamp 
    AFTER UPDATE ON cameras
    BEGIN
        UPDATE cameras SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- =====================================================
-- DADOS INICIAIS (SEED DATA)
-- =====================================================

-- Configurações padrão do sistema
INSERT INTO configuracoes_sistema (chave, valor, tipo, descricao, categoria) VALUES
('sistema_nome', 'SIAC Industrial', 'string', 'Nome do sistema', 'geral'),
('max_cameras_simultaneas', '8', 'integer', 'Máximo de câmeras processando simultaneamente', 'performance'),
('intervalo_heartbeat', '30', 'integer', 'Intervalo de heartbeat em segundos', 'comunicacao'),
('timeout_camera', '10', 'integer', 'Timeout para câmera offline em segundos', 'monitoramento'),
('debug_enabled', 'false', 'boolean', 'Habilitar modo debug', 'desenvolvimento'),
('log_level', 'INFO', 'string', 'Nível de log padrão', 'desenvolvimento');

-- Setor padrão para testes
INSERT INTO setores (nome, descricao) VALUES 
('Produção', 'Setor principal de produção');

-- Linha padrão para testes
INSERT INTO linhas (setor_id, nome, descricao) VALUES 
(1, 'Linha 01', 'Linha de produção principal');

-- Produto padrão para testes
INSERT INTO produtos (nome, descricao) VALUES 
('Produto Padrão', 'Configuração padrão para testes');
