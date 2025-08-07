/**
 * SIAC Industrial Dashboard - UI Components
 * Componentes reutilizáveis para interface industrial
 */

export class UIComponents {
    constructor() {
        this.statusIcons = {
            online: '🟢',
            offline: '🔴',
            warning: '🟡',
            unknown: '⚪'
        };
        
        this.statusTexts = {
            online: 'Online',
            offline: 'Offline',
            warning: 'Atenção',
            unknown: 'Desconhecido'
        };
    }
    
    /**
     * Cria card de setor com linhas e câmeras
     */
    createSetorCard(setor, cameras) {
        const setorCameras = cameras.filter(c => c.setor_id === setor.id);
        const linhas = this.groupCamerasByLinha(setorCameras);
        
        const card = document.createElement('div');
        card.className = 'setor-card';
        card.innerHTML = `
            <div class="setor-header">
                <div class="setor-title">${setor.nome}</div>
            </div>
            
            <div class="setor-stats">
                <span>📹 ${setorCameras.length} câmeras</span>
                <span>🏭 ${linhas.length} linhas</span>
                <span>${this.getSetorStatusIcon(setorCameras)} ${this.getSetorStatusText(setorCameras)}</span>
            </div>
            
            <div class="setor-content">
                <div class="linhas-list">
                    ${linhas.map(linha => this.createLinhaItem(linha, setorCameras)).join('')}
                </div>
            </div>
        `;
        
        return card;
    }
    
    /**
     * Agrupa câmeras por linha
     */
    groupCamerasByLinha(cameras) {
        const linhasMap = new Map();
        
        cameras.forEach(camera => {
            const linhaId = camera.linha_id;
            const linhaNome = camera.linha_nome || `Linha ${linhaId}`;
            
            if (!linhasMap.has(linhaId)) {
                linhasMap.set(linhaId, {
                    id: linhaId,
                    nome: linhaNome,
                    cameras: []
                });
            }
            
            linhasMap.get(linhaId).cameras.push(camera);
        });
        
        return Array.from(linhasMap.values());
    }
    
    /**
     * Cria item de linha com câmeras
     */
    createLinhaItem(linha, allCameras) {
        const linhaCameras = allCameras.filter(c => c.linha_id === linha.id);
        
        return `
            <div class="linha-item" data-linha-id="${linha.id}">
                <div class="linha-info">
                    <div class="linha-name">🏭 ${linha.nome}</div>
                    <div class="linha-cameras">${linhaCameras.length} câmeras</div>
                </div>
                
                <div class="camera-status-dots">
                    ${linhaCameras.map(camera => this.createCameraDot(camera)).join('')}
                </div>
                
                <button class="btn btn-sm btn-secondary" onclick="window.siacDashboard.showLinhaDetails(${linha.id})">
                    <span class="btn-icon">👁️</span> Ver Detalhes
                </button>
            </div>
        `;
    }
    
    /**
     * Cria ponto de status da câmera
     */
    createCameraDot(camera) {
        const status = this.getCameraStatus(camera);
        const title = `${camera.nome} - ${this.statusTexts[status]}`;
        
        return `
            <div class="camera-dot ${status}" 
                 data-camera-id="${camera.id}"
                 title="${title}"
                 onclick="window.siacDashboard.showCameraModal(${camera.id})">
            </div>
        `;
    }
    
    /**
     * Determina status da câmera
     */
    getCameraStatus(camera) {
        if (!camera.status) return 'unknown';
        
        if (camera.status.running) {
            if (camera.status.error) return 'warning';
            return 'online';
        }
        
        return 'offline';
    }
    
    /**
     * Obtém ícone de status do setor
     */
    getSetorStatusIcon(cameras) {
        if (cameras.length === 0) return '⚪';
        
        const onlineCameras = cameras.filter(c => c.status?.running).length;
        const totalCameras = cameras.length;
        
        if (onlineCameras === totalCameras) return '🟢';
        if (onlineCameras === 0) return '🔴';
        return '🟡';
    }
    
    /**
     * Obtém texto de status do setor
     */
    getSetorStatusText(cameras) {
        if (cameras.length === 0) return 'Sem câmeras';
        
        const onlineCameras = cameras.filter(c => c.status?.running).length;
        const totalCameras = cameras.length;
        
        if (onlineCameras === totalCameras) return 'Operacional';
        if (onlineCameras === 0) return 'Parado';
        return `${onlineCameras}/${totalCameras} ativas`;
    }
    
    /**
     * Cria conteúdo detalhado da câmera para modal
     */
    createCameraDetailContent(camera) {
        const status = this.getCameraStatus(camera);
        const produto = this.getProdutoName(camera.produto_id);
        
        return `
            <div class="camera-details">
                <div class="camera-info-grid">
                    <div class="info-item">
                        <label>📹 Nome:</label>
                        <span>${camera.nome}</span>
                    </div>
                    
                    <div class="info-item">
                        <label>🏭 Setor/Linha:</label>
                        <span>${camera.setor_nome || 'N/A'} / ${camera.linha_nome || 'N/A'}</span>
                    </div>
                    
                    <div class="info-item">
                        <label>📦 Produto:</label>
                        <span>${produto}</span>
                    </div>
                    
                    <div class="info-item">
                        <label>🔗 Conexão:</label>
                        <span>${camera.device_index ? `USB ${camera.device_index}` : camera.ip_address || 'N/A'}</span>
                    </div>
                    
                    <div class="info-item">
                        <label>📊 Status:</label>
                        <span class="status-badge status-${status}">
                            ${this.statusIcons[status]} ${this.statusTexts[status]}
                        </span>
                    </div>
                    
                    <div class="info-item">
                        <label>⏱️ Última atualização:</label>
                        <span>${camera.status?.last_update ? new Date(camera.status.last_update).toLocaleString('pt-BR') : 'N/A'}</span>
                    </div>
                </div>
                
                ${this.createCameraStats(camera)}
                
                <div class="camera-controls">
                    <h4>🎛️ Controles</h4>
                    <div class="control-buttons">
                        ${camera.status?.running ? 
                            `<button class="btn btn-error" data-action="stop" data-camera="${camera.id}">
                                <span class="btn-icon">⏹️</span> Parar Câmera
                            </button>` :
                            `<button class="btn btn-success" data-action="start" data-camera="${camera.id}">
                                <span class="btn-icon">▶️</span> Iniciar Câmera
                            </button>`
                        }
                        
                        <button class="btn btn-secondary" data-action="change-product" data-camera="${camera.id}">
                            <span class="btn-icon">📦</span> Alterar Produto
                        </button>
                        
                        <button class="btn btn-secondary" onclick="window.siacDashboard.refreshCameraStatus(${camera.id})">
                            <span class="btn-icon">🔄</span> Atualizar Status
                        </button>
                    </div>
                </div>
                
                ${camera.status?.error ? this.createErrorSection(camera.status.error) : ''}
            </div>
        `;
    }
    
    /**
     * Cria seção de estatísticas da câmera
     */
    createCameraStats(camera) {
        if (!camera.status || !camera.status.running) {
            return '<div class="camera-stats"><p>📊 Estatísticas disponíveis quando câmera estiver ativa</p></div>';
        }
        
        return `
            <div class="camera-stats">
                <h4>📊 Estatísticas</h4>
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-value">${camera.status.fps || 0}</span>
                        <span class="stat-label">FPS</span>
                    </div>
                    
                    <div class="stat-item">
                        <span class="stat-value">${camera.detection?.contagem || 0}</span>
                        <span class="stat-label">Itens Detectados</span>
                    </div>
                    
                    <div class="stat-item">
                        <span class="stat-value">${camera.detection?.estado || 'N/A'}</span>
                        <span class="stat-label">Estado Atual</span>
                    </div>
                    
                    <div class="stat-item">
                        <span class="stat-value">${camera.status.uptime || '0s'}</span>
                        <span class="stat-label">Tempo Ativo</span>
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * Cria seção de erro
     */
    createErrorSection(error) {
        return `
            <div class="error-section">
                <h4>❌ Erro</h4>
                <div class="error-message">
                    <code>${error}</code>
                </div>
            </div>
        `;
    }
    
    /**
     * Cria lista de produtos para seleção
     */
    createProductList(produtos, currentProductId) {
        if (!produtos || produtos.length === 0) {
            return '<p>Nenhum produto disponível</p>';
        }
        
        return produtos.map(produto => `
            <div class="product-item ${produto.id === currentProductId ? 'selected' : ''}" 
                 data-product-id="${produto.id}">
                <div class="product-info">
                    <div class="product-name">📦 ${produto.nome}</div>
                    <div class="product-description">${produto.descricao || 'Produto YOLO'}</div>
                    <div class="product-meta">
                        <span>🎯 Modelo: ${produto.modelo_yolo}</span>
                        <span>📏 Versão: ${produto.versao}</span>
                    </div>
                </div>
                
                <div class="product-status">
                    ${produto.ativo ? 
                        '<span class="status-badge status-online">✅ Ativo</span>' : 
                        '<span class="status-badge status-offline">❌ Inativo</span>'
                    }
                </div>
            </div>
        `).join('');
    }
    
    /**
     * Obtém nome do produto por ID
     */
    getProdutoName(produtoId) {
        // Esta função será implementada quando tivermos acesso aos dados de produtos
        // Por enquanto, retorna um placeholder
        return produtoId ? `Produto ${produtoId}` : 'Nenhum produto selecionado';
    }
    
    /**
     * Cria card de alerta
     */
    createAlertCard(alert) {
        const severityClass = this.getSeverityClass(alert.severity);
        const severityIcon = this.getSeverityIcon(alert.severity);
        
        return `
            <div class="alert-card ${severityClass}">
                <div class="alert-header">
                    <span class="alert-icon">${severityIcon}</span>
                    <span class="alert-title">${alert.title || 'Alerta'}</span>
                    <span class="alert-time">${new Date(alert.timestamp).toLocaleTimeString('pt-BR')}</span>
                </div>
                
                <div class="alert-message">
                    ${alert.message}
                </div>
                
                ${alert.camera_id ? `
                    <div class="alert-source">
                        📹 Câmera: ${alert.camera_name || alert.camera_id}
                    </div>
                ` : ''}
                
                <div class="alert-actions">
                    <button class="btn btn-sm btn-secondary" onclick="window.siacDashboard.acknowledgeAlert('${alert.id}')">
                        ✅ Reconhecer
                    </button>
                    
                    ${alert.camera_id ? `
                        <button class="btn btn-sm btn-primary" onclick="window.siacDashboard.showCameraModal(${alert.camera_id})">
                            👁️ Ver Câmera
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    }
    
    /**
     * Obtém classe CSS para severidade
     */
    getSeverityClass(severity) {
        const classes = {
            'error': 'alert-error',
            'warning': 'alert-warning',
            'info': 'alert-info',
            'success': 'alert-success'
        };
        
        return classes[severity] || 'alert-info';
    }
    
    /**
     * Obtém ícone para severidade
     */
    getSeverityIcon(severity) {
        const icons = {
            'error': '🚨',
            'warning': '⚠️',
            'info': 'ℹ️',
            'success': '✅'
        };
        
        return icons[severity] || 'ℹ️';
    }
    
    /**
     * Cria indicador de loading
     */
    createLoadingIndicator(text = 'Carregando...') {
        return `
            <div class="loading-indicator">
                <div class="loading-spinner"></div>
                <span class="loading-text">${text}</span>
            </div>
        `;
    }
    
    /**
     * Cria card vazio/placeholder
     */
    createEmptyCard(title, message, actionText = null, actionCallback = null) {
        return `
            <div class="empty-card">
                <div class="empty-icon">📭</div>
                <div class="empty-title">${title}</div>
                <div class="empty-message">${message}</div>
                
                ${actionText && actionCallback ? `
                    <button class="btn btn-primary" onclick="${actionCallback}">
                        ${actionText}
                    </button>
                ` : ''}
            </div>
        `;
    }
    
    /**
     * Cria breadcrumb navigation
     */
    createBreadcrumb(items) {
        return items.map((item, index) => {
            const isLast = index === items.length - 1;
            const isClickable = item.url && !isLast;
            
            if (isClickable) {
                return `<a href="${item.url}" class="breadcrumb-item">${item.text}</a>`;
            } else {
                return `<span class="breadcrumb-item ${isLast ? 'active' : ''}">${item.text}</span>`;
            }
        }).join(' › ');
    }
    
    /**
     * Cria tabela responsiva
     */
    createResponsiveTable(headers, rows, options = {}) {
        const { sortable = false, searchable = false, pagination = false } = options;
        
        return `
            <div class="table-container">
                ${searchable ? `
                    <div class="table-search">
                        <input type="text" class="search-input" placeholder="🔍 Buscar...">
                    </div>
                ` : ''}
                
                <table class="responsive-table">
                    <thead>
                        <tr>
                            ${headers.map(header => `
                                <th ${sortable ? 'class="sortable"' : ''}>
                                    ${header}
                                    ${sortable ? '<span class="sort-icon">↕️</span>' : ''}
                                </th>
                            `).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        ${rows.map(row => `
                            <tr>
                                ${row.map(cell => `<td>${cell}</td>`).join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
                
                ${pagination ? `
                    <div class="table-pagination">
                        <button class="btn btn-sm btn-secondary">← Anterior</button>
                        <span class="pagination-info">Página 1 de 1</span>
                        <button class="btn btn-sm btn-secondary">Próximo →</button>
                    </div>
                ` : ''}
            </div>
        `;
    }
}

export default UIComponents;
