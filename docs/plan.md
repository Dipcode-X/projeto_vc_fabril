# Plano Estratégico - Arquitetura SIAC Industrial

## Visão Geral

### Arquitetura Centralizada
- **Backend FastAPI** como ponto único de orquestração e integração
- **SiacOrchestrator** substitui o papel do main.py, gerenciando múltiplas câmeras simultaneamente
- **SiacProcessor** executa instâncias individuais do legacy para cada câmera/produto
- **Configurações dinâmicas** carregadas do banco SQL para máxima flexibilidade

### Modularização Equilibrada
- **Arquivos pequenos** (50-150 linhas) com responsabilidades únicas
- **Estrutura clara**: main.py → orchestrator.py → camera_processor.py → endpoints/
- **Fácil manutenção** e evolução sem complexidade excessiva

### Funcionalidades do Dashboard
- **Navegação**: Setores → Linhas de Produção
- **Controle dinâmico**: Ativar/desativar câmeras por linha
- **Seleção de produtos**: Dropdown com modelos YOLO específicos
- **Monitoramento**: Status em tempo real e métricas de produção

---

## Estrutura do Projeto

```
central_manager/
├── api/
│   ├── main.py                    # FastAPI entry point (~50 linhas)
│   ├── orchestrator.py            # SiacOrchestrator (~120 linhas)
│   ├── camera_processor.py        # SiacProcessor (~100 linhas)
│   └── endpoints/
│       ├── cameras.py            # APIs de câmeras (~60 linhas)
│       ├── produtos.py           # APIs de produtos (~60 linhas)
│       └── dashboard.py          # APIs do dashboard (~60 linhas)
├── core_simple/                   # StateManager para produtos 1 camada
├── core_advanced/                 # StateManager para produtos 2 camadas (legacy)
├── shared/                        # Utilitários comuns (logger, config_loader)
├── database/                      # Schema e conexão SQL
└── static/                        # Frontend assets
```

---

## Componentes Principais

### SiacOrchestrator 
*O "cérebro central" que substitui o main.py*
- **Gerencia** múltiplas câmeras simultaneamente
- **Carrega** configurações dinâmicas do banco SQL
- **Seleciona** StateManager adequado (simple/advanced)
- **Monitora** status global e métricas de produção

### SiacProcessor
*Instância individual do legacy para cada câmera*
- **Processa** 1 câmera específica em thread separada
- **Executa** o mesmo código robusto do legacy
- **Usa** produto/modelos específicos carregados dinamicamente

### Core Modules
- **core_simple/**: StateManager básico para produtos 1 camada
- **core_advanced/**: StateManager robusto do legacy para produtos 2 camadas
- **shared/**: Utilitários comuns (logger, config_loader, etc.)

---

## Task List

### Concluído
- [x] Definir arquitetura centralizada com FastAPI como ponto único de orquestração
- [x] Planejar modularização: Orchestrator, CameraProcessor, endpoints separados
- [x] Estruturar pastas core_simple, core_advanced e shared para lógica dos StateManagers
- [x] Validar funcionamento do legacy e corrigir caminhos dos modelos
- [x] Limpar projeto removendo arquivos/pastas desnecessários

### Em Andamento
- [ ] **Copiar/adaptar arquivos do legacy para core_advanced**
  - [ ] state_manager.py → state_manager_advanced.py
  - [ ] detector.py → detector_advanced.py  
  - [ ] config.py → config_advanced.py
- [ ] **Criar utilitários em shared/**
  - [ ] logger_config.py (do legacy)
  - [ ] config_loader.py (novo - carrega do banco)

### Próximas Etapas
- [ ] Criar versões simplificadas em core_simple para produtos de 1 camada
- [ ] Implementar orchestrator.py: gerenciamento de múltiplas câmeras/processadores
- [ ] Implementar camera_processor.py: processamento isolado por câmera
- [ ] Modularizar endpoints: cameras, produtos, dashboard
- [ ] Integrar carregamento dinâmico de configurações do banco SQL
- [ ] Implementar APIs REST/WebSocket para controle e monitoramento
- [ ] Validar integração frontend-backend com seleção dinâmica de produto/câmera
- [ ] Testar arquitetura com múltiplas câmeras e produtos

---

## Current Goal
**Copiar/adaptar arquivos do legacy para core_advanced e iniciar implementação do Orchestrator**

---

## Princípios Arquiteturais

### Simplicidade
- Código limpo e direto
- Arquivos pequenos e focados
- Responsabilidades bem definidas

### Flexibilidade
- Configurações dinâmicas via banco SQL
- Suporte a múltiplos produtos/modelos
- Ativação/desativação dinâmica de câmeras

### Robustez
- Baseado no legacy testado e aprovado
- Isolamento entre câmeras (falha em 1 não afeta outras)
- Monitoramento e logs centralizados

### Escalabilidade
- N câmeras simultâneas
- Fácil adição de novos produtos
- Estrutura preparada para crescimento industrial
