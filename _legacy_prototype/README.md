# 📦 Legacy Prototype - SIAC Original

Esta pasta contém o **protótipo original** do SIAC que foi desenvolvido e testado com sucesso.

## 📁 Conteúdo

### 🔧 Componentes Principais
- **`main.py`** - Aplicação principal do protótipo
- **`detector.py`** - Detector original (base para refatoração)
- **`state_manager.py`** - ⭐ **Lógica robusta de estados** (36KB de código testado)
- **`visualizer.py`** - Interface visual funcionando
- **`config.py`** - Configurações base do sistema

### 🛠️ Utilitários
- **`logger_config.py`** - Sistema de logging estruturado
- **`capturador_imagens.py`** - Captura de imagens para dataset
- **`extrator_frames.py`** - Extração de frames de vídeos
- **`organizar_dataset.py`** - Organização de datasets
- **`train.py`** - Script de treinamento dos modelos

## ✅ Status do Protótipo

- ✅ **Funcionando 100%** - Sistema completo testado
- ✅ **Lógica robusta** - Anti-falsos positivos/negativos
- ✅ **Sistema de alertas** - Debounce e carência implementados
- ✅ **Memória espacial** - Prevenção de recontagem entre camadas
- ✅ **Tolerância a oclusões** - Sistema estável

## 🔄 Reutilização

Estes arquivos servem como **referência** para:
- Resgatar lógica específica do `state_manager.py`
- Reutilizar componentes visuais do `visualizer.py`
- Consultar configurações do `config.py`
- Referência de implementação funcionando

## 🚀 Evolução

O protótipo evoluiu para a **estrutura modular** em `/siac_industrial/`:
- Arquitetura industrial
- Configuração dinâmica
- Comunicação centralizada
- Múltiplos produtos/perfis

---

*Backup criado em: 2025-01-28*
*Status: Protótipo funcional preservado*
